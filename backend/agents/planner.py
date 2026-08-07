"""Planner agent — drafts a plan ONLY from the approved runbook catalog (runbook-bounded action
space, domain-guardrails.md pillar (a)): free-text remediation can only be raised as a proposal
for a new runbook, routed to a human, never executed directly. Uses gpt-4.1-nano — the
human-approved substitute for the deprecated DeepSeek V3 deployment (models-routing.md
"CONFIRMED UNREACHABLE", decisions-log.md). Blast radius and the policy gate result are computed
deterministically AFTER the LLM drafts the plan, never delegated to the model.
"""
import json
import os
from datetime import datetime, timezone

import api_client
from guardrails.blast_radius import compute_blast_radius
from guardrails.policy_gate import PolicyContext, PolicyRequest, evaluate_policy
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TERMINATION_CAP_EXCEEDED, TurnCapExceeded, TurnTracker
from orchestrator.retrieval import query_collection

PLANNER_MODEL = "azure/genailab-maas-gpt-4.1-nano"  # DeepSeek V3 substitute, see models-routing.md
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")


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
    response = None

    try:
        tracker.use_turn()
        query_text = f"{runbook_class} {ci['type']}: {hypothesis.get('text', '')}"
        chunks = query_collection("runbooks", query_text, n_results=4, where={"class": runbook_class})

        if not chunks:
            termination_reason = "no_valid_runbook_found"
        else:
            valid_chunk_ids = {c["id"] for c in chunks}
            tracker.use_turn()
            llm = api_client.get_llm(model=PLANNER_MODEL, temperature=0)
            response = llm.invoke(_build_prompt(hypothesis, chunks))
            plan = _parse_and_filter_steps(response.content, valid_chunk_ids)
            cited_artifact_ids = sorted({s["cites_runbook_step"] for s in plan["steps"]})
            termination_reason = "plan_drafted" if plan["steps"] else "no_valid_runbook_found"
    except TurnCapExceeded:
        termination_reason = TERMINATION_CAP_EXCEEDED

    blast_radius = compute_blast_radius(ci["id"], _load_relationships())
    policy_result = evaluate_policy(
        PolicyRequest(
            ci_id=ci["id"], environment=ci["environment"], criticality=ci["criticality"],
            blast_radius_count=blast_radius["count"], action_type=runbook_class,
            requested_at=datetime.now(timezone.utc).isoformat(), actor_role=actor_role,
        ),
        PolicyContext(),
    )
    plan["blast_radius"] = blast_radius
    plan["policy_gate_result"] = {"decision": policy_result.decision, "triggered_rules": policy_result.triggered_rules, "reasons": policy_result.reasons}

    return SpecialistResult(
        agent_name="planner", incident_id=incident_id,
        result=plan, cited_artifact_ids=cited_artifact_ids,
        confidence=1.0 if plan["steps"] else 0.0,
        turns_used=tracker.turns_used, termination_reason=termination_reason,
        tokens_used=api_client.extract_token_usage(response) if response is not None else None,
    )
