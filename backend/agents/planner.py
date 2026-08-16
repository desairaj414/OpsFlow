"""Planner agent — drafts a plan ONLY from the approved runbook catalog (runbook-bounded action
space, domain-guardrails.md pillar (a)): free-text remediation can only be raised as a proposal
for a new runbook, routed to a human, never executed directly. Uses the active provider's
"structured"-role model (models-routing.md — reliable valid-JSON output at a normal token budget;
e.g. gpt-4.1-nano on TCS, the human-approved substitute for the deprecated DeepSeek V3 deployment,
decisions-log.md). Blast radius and the policy gate result are computed deterministically AFTER
the LLM drafts the plan, never delegated to the model.
"""
import json
import os
import sqlite3
import time
from datetime import datetime, timezone

import api_client
import mcp_servers.patch_mcp as patch_mcp
from guardrails.blast_radius import compute_blast_radius
from guardrails.policy_gate import PolicyContext, PolicyRequest, evaluate_policy
from guardrails.scheduling import propose_maintenance_window
from orchestrator import cache
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TERMINATION_CAP_EXCEEDED, TurnCapExceeded, TurnTracker
from orchestrator.retrieval import query_collection

_PROMPT_VERSION = "planner-v1"  # bump if _build_prompt's template changes, so old cache rows don't leak in

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")


async def _load_policy_context(environment: str, runbook_class: str) -> PolicyContext:
    """Builds a real PolicyContext instead of the always-empty one this used to pass — found
    2026-08-17 (future-plans.md) that FREEZE_WINDOW/MAX_CONCURRENT_CHANGES were fully built,
    unit-tested (test_policy_gate.py), and never actually reachable because of this gap.

    freeze_windows: reuses the same patch_mcp.get_change_calendar(scope=...) call the Patch
    Management maintenance-window logic already makes below — not a second way to read
    change_calendar.json. Only global- and environment-scoped blackouts are included; a
    CI-specific blackout (get_change_calendar also supports scope=<ci_id>) isn't representable in
    PolicyContext's tested {environment, start, end} shape, so it stays out of scope for the
    general policy gate (Patch Management's own maintenance-window proposal still sees it).

    **Scoped to runbook_class == "patching" only** (checked by the caller, not this docstring —
    see below): change-freeze windows are a change-management concept, and `patching` is this
    project's own planned-change workflow type. Tried wiring it universally first and immediately
    broke 4 supervisor tests, all `remediation`/`tuning` workflows getting blocked by
    `change_calendar.json`'s BLACKOUT-G01 — that window happens to span whatever "now" is at the
    time this is run (deliberate, so the Patch Management demo always has a current blackout to
    show). Blocking incident remediation because of an unrelated code-freeze isn't correct
    behavior — real ITSM practice exempts emergency/break-fix work from standard change freezes —
    and it isn't what the existing tests (correctly) expect either.

    active_changes_in_environment: COUNT of local_tickets rows with status_normalized ==
    'needs_approval' in this environment. Deliberately not any other status — 'needs_approval' is
    set exclusively by a live run pausing for a human decision (main.py's _persist_ticket_snapshot);
    the 4000 bulk-seeded historical rows (data_gen/local_tickets_bulk.py) only ever produce
    resolved/in_progress/open, so this can't be inflated by seed data the way a naive "any
    non-resolved ticket" count would be (confirmed directly: that naive count is in the hundreds
    per environment, which would block nearly every prod run outright — not what this rule is for).
    Applied to every workflow type (not patching-only) — proven not to regress any existing test."""
    freeze_windows: list[dict] = []
    if runbook_class == "patching":
        try:
            calendar_resp = await patch_mcp.get_change_calendar(scope=environment)
            freeze_windows = [
                {"environment": environment, "start": w["starts_at"], "end": w["ends_at"]}
                for w in calendar_resp["blackouts"]
            ]
        except Exception:
            pass  # patch-source simulator unavailable — degrade to no known freeze windows, don't crash the chain

    active_changes = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM local_tickets lt JOIN cmdb_ci c ON c.id = lt.cmdb_ci "
                "WHERE c.environment = ? AND lt.status_normalized = 'needs_approval'",
                (environment,),
            ).fetchone()
            active_changes = row[0] if row else 0
        finally:
            conn.close()
    except Exception:
        pass  # DB unavailable in this context — degrade to 0, don't crash the chain

    return PolicyContext(active_changes_in_environment=active_changes, freeze_windows=freeze_windows)


def _load_relationships() -> list[dict]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return json.load(f)["relationships"]


def _build_prompt(hypothesis: dict, chunks: list[dict]) -> str:
    valid_chunk_ids = [c["id"] for c in chunks]
    chunks_block = "\n\n".join(f"[{c['id']}] ({c['metadata'].get('heading_path', '')}):\n{c['document']}" for c in chunks)
    return f"""You are drafting a remediation plan. ONLY use the runbook steps provided below —
never invent a step. Every plan step MUST cite exactly one of these chunk IDs: {valid_chunk_ids}

DIAGNOSIS HYPOTHESIS: {hypothesis.get('text', '(none)')}

AVAILABLE RUNBOOK STEPS:
{chunks_block}

Respond with ONLY valid JSON (no markdown fences), this exact shape:
{{"runbook_id": "...", "steps": [{{"step_no": 1, "action": "...", "cites_runbook_step": "<chunk id from the list above>"}}]}}
"""


def _parse_and_filter_steps(raw_content: str, valid_chunk_ids: set[str]) -> dict:
    content = raw_content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    parsed = json.loads(content)
    steps = parsed.get("steps", [])
    # Runbook-bounded action space: drop any step citing a chunk not actually retrieved.
    bounded_steps = [s for s in steps if s.get("cites_runbook_step") in valid_chunk_ids]
    return {"runbook_id": parsed.get("runbook_id", ""), "steps": bounded_steps}


async def run_planner(incident_id: str, ci: dict, runbook_class: str, hypothesis: dict, actor_role: str = "operator") -> SpecialistResult:
    tracker = TurnTracker("planner")
    termination_reason = "no_valid_runbook_found"
    plan: dict = {"runbook_id": "", "steps": []}
    cited_artifact_ids: list[str] = []
    tokens_used: int | None = None
    model_used: str | None = None
    cache_hit: bool | None = None

    try:
        tracker.use_turn()
        query_text = f"{runbook_class} {ci['type']}: {hypothesis.get('text', '')}"
        chunks = query_collection("runbooks", query_text, n_results=4, where={"class": runbook_class})

        if not chunks:
            termination_reason = "no_valid_runbook_found"
        else:
            valid_chunk_ids = {c["id"] for c in chunks}
            tracker.use_turn()
            prompt = _build_prompt(hypothesis, chunks)
            key = cache.cache_key(_PROMPT_VERSION, prompt)
            cached = cache.check_cache(key)
            if cached is not None:
                content, tokens_used, model_used, cache_hit = cached.content, cached.tokens, cached.model, True
            else:
                llm = api_client.get_llm(role="structured", temperature=0)
                # .ainvoke(), not .invoke() — this is an async def handler; a sync call here blocks
                # uvicorn's single-threaded event loop for the whole gateway round-trip, stalling every
                # other request the backend is serving (SSE stream, unrelated fetches) until it returns.
                # Real, demonstrated impact once auto-triage started running diagnosis continuously in
                # the background — see errors-solved.md.
                start = time.perf_counter()
                response = await llm.ainvoke(prompt)
                elapsed_ms = (time.perf_counter() - start) * 1000
                content = response.content
                tokens_used = api_client.extract_token_usage(response)
                model_used = api_client.extract_model_used(response)
                cache_hit = False
            plan = _parse_and_filter_steps(content, valid_chunk_ids)
            cited_artifact_ids = sorted({s["cites_runbook_step"] for s in plan["steps"]})
            termination_reason = "plan_drafted" if plan["steps"] else "no_valid_runbook_found"
            if cache_hit is False:
                cache.store_cache(key, content, tokens_used, elapsed_ms, model_used)
    except TurnCapExceeded:
        termination_reason = TERMINATION_CAP_EXCEEDED

    blast_radius = compute_blast_radius(ci["id"], _load_relationships())
    policy_context = await _load_policy_context(ci["environment"], runbook_class)
    policy_result = evaluate_policy(
        PolicyRequest(
            ci_id=ci["id"], environment=ci["environment"], criticality=ci["criticality"],
            blast_radius_count=blast_radius["count"], action_type=runbook_class,
            requested_at=datetime.now(timezone.utc).isoformat(), actor_role=actor_role,
        ),
        policy_context,
    )
    plan["blast_radius"] = blast_radius
    plan["policy_gate_result"] = {"decision": policy_result.decision, "triggered_rules": policy_result.triggered_rules, "reasons": policy_result.reasons}

    # Patch Management's plan_output (domain-workflows.md parity table: "Grouped maintenance
    # window") — deterministic rule engine (guardrails/scheduling.py), computed the same way
    # blast_radius/policy_gate_result are: AFTER the LLM drafts the plan, never delegated to it.
    if runbook_class == "patching":
        try:
            patches_resp = await patch_mcp.get_pending_patches(ci_id=ci["id"])
            calendar_resp = await patch_mcp.get_change_calendar(scope=ci["environment"])
            plan["maintenance_window"] = propose_maintenance_window(
                ci_id=ci["id"], environment=ci["environment"],
                pending_patches=patches_resp["patches"], change_calendar=calendar_resp["blackouts"],
            )
        except Exception:
            plan["maintenance_window"] = None  # patch-source simulator unavailable — degrade, don't crash the chain

    return SpecialistResult(
        agent_name="planner", incident_id=incident_id,
        result=plan, cited_artifact_ids=cited_artifact_ids,
        confidence=1.0 if plan["steps"] else 0.0,
        turns_used=tracker.turns_used, termination_reason=termination_reason,
        tokens_used=tokens_used, model_used=model_used, cache_hit=cache_hit,
    )
