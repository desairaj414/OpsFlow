"""Supervisor — dispatch loop + schema validation of each specialist's typed result before
dispatching the next agent (domain-agents.md). Two levels only: Supervisor + specialists; agents
never call each other directly (decisions-log.md, do not re-decide).

Steps in the workflow YAML that are NOT separate schema-validated specialists, and why:
  - correlate   — Phase 2's deterministic correlation engine; the Supervisor receives an
                  already-clustered alert group as input, it just logs the step.
  - policy_gate — computed deterministically INSIDE the Planner's result (guardrails/policy_gate.py
                  called from agents/planner.py) — there is no separate policy_gate agent.
  - approval    — a human decision point; the workflow pauses here (returns "pending_approval")
                  unless auto_approve is explicitly passed (demo/test convenience only).
  - execute     — Supervisor-internal: records the action in the audit log. Per decisions-log.md
                  ("no real script execution against live infrastructure"), what "executes" is the
                  simulated world already captured in the Phase 1 metric data — a CI seeded with a
                  genuine degradation curve stays degraded regardless of what "execute" does, which
                  is exactly what lets Verification's Fake Fix Detector tell a real fix from a fake
                  one on real data, not a scripted answer.
"""
import csv
import os
import sqlite3
import time

import mcp_servers.itsm_mcp as itsm_mcp
from a2a.client import invoke_diagnosis_via_a2a
from agents.enrichment import run_enrichment
from agents.knowledge import run_knowledge
from agents.planner import run_planner
from agents.sync import run_sync
from agents.verification import run_verification
from orchestrator.audit import write_audit_entry
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TERMINATION_CAP_EXCEEDED

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")


def load_workflow(workflow_type: str) -> dict:
    path = os.path.join(WORKFLOWS_DIR, f"{workflow_type}.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate(result: SpecialistResult) -> SpecialistResult:
    """Defensive re-validation boundary: even though agents already construct a typed
    SpecialistResult, the Supervisor re-validates the serialized form before trusting it,
    the way it would have to if a specialist crossed a real process/network boundary."""
    return SpecialistResult.model_validate(result.model_dump())


async def _timed(coro, transport: str = "in_process") -> SpecialistResult:
    """Brackets a specialist call to fill in the Agent Trace Viewer's latency/transport fields —
    agents themselves don't know how the Supervisor is invoking them (in-process vs A2A)."""
    start = time.perf_counter()
    result = _validate(await coro)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result.model_copy(update={"latency_ms": elapsed_ms, "transport": transport})


def _load_metric_series(ci_id: str) -> list[dict] | None:
    path = os.path.join(DATA_DIR, "metrics", f"{ci_id}.csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def run_workflow(
    incident_id: str, ci: dict, alerts: list[dict], workflow_type: str,
    actor_role: str = "operator", auto_approve: bool = False,
) -> dict:
    workflow = load_workflow(workflow_type)
    conn = sqlite3.connect(DB_PATH)
    trace: list[SpecialistResult] = []

    try:
        write_audit_entry(conn, actor="supervisor", action="correlate", target_artifact=incident_id,
                           evidence_ids=[a["id"] for a in alerts], input_modality="alert")

        enrichment_result = await _timed(run_enrichment(incident_id, ci["id"], alerts))
        trace.append(enrichment_result)
        write_audit_entry(conn, actor="agent:enrichment", action="gather_evidence", target_artifact=incident_id,
                           evidence_ids=enrichment_result.cited_artifact_ids)
        if enrichment_result.termination_reason == TERMINATION_CAP_EXCEEDED or not enrichment_result.result["evidence"]:
            return {"status": "stopped", "reason": "enrichment_failed", "trace": trace}

        ticket = await itsm_mcp.create_ticket(
            short_description=f"[{workflow_type}] {incident_id}: {ci['name']}", priority="P2", cmdb_ci=ci["id"],
        )
        sys_id = ticket["result"]["sys_id"]

        # The one handoff that travels over A2A (domain-agents.md) — everything else in this loop
        # is an in-process typed-contract call.
        diagnosis_result = await _timed(
            invoke_diagnosis_via_a2a(incident_id, enrichment_result.result["evidence"]), transport="a2a"
        )
        trace.append(diagnosis_result)
        write_audit_entry(conn, actor="agent:diagnosis", action="generate_hypotheses", target_artifact=incident_id,
                           evidence_ids=diagnosis_result.cited_artifact_ids, model_used="azure_ai/genailab-maas-DeepSeek-R1")
        if not diagnosis_result.result["hypotheses"]:
            return {"status": "stopped", "reason": "no_valid_hypotheses", "trace": trace, "sys_id": sys_id}
        top_hypothesis = diagnosis_result.result["hypotheses"][0]

        planner_result = await _timed(run_planner(incident_id, ci, workflow["runbook_class"], top_hypothesis, actor_role))
        trace.append(planner_result)
        write_audit_entry(conn, actor="agent:planner", action="draft_plan", target_artifact=incident_id,
                           evidence_ids=planner_result.cited_artifact_ids, model_used="azure/genailab-maas-gpt-4.1-nano")
        policy_decision = planner_result.result["policy_gate_result"]["decision"]
        if policy_decision == "block":
            return {"status": "blocked", "reason": planner_result.result["policy_gate_result"]["reasons"], "trace": trace, "sys_id": sys_id}

        if policy_decision == "needs_approval" and not auto_approve:
            return {"status": "pending_approval", "trace": trace, "sys_id": sys_id}
        write_audit_entry(conn, actor=actor_role, action="approve_plan", target_artifact=incident_id, approval_ref=f"APR-{incident_id}")

        write_audit_entry(conn, actor="supervisor", action="execute_plan", target_artifact=incident_id,
                           evidence_ids=[s["cites_runbook_step"] for s in planner_result.result["steps"]])
        alert_cleared = True  # plan ran without error in this simulated world — see module docstring

        metric_series = _load_metric_series(ci["id"])
        verification_result = await _timed(run_verification(incident_id, alert_cleared, metric_series))
        trace.append(verification_result)
        write_audit_entry(conn, actor="agent:verification", action="verify_resolution", target_artifact=incident_id)

        sync_result = await _timed(run_sync(incident_id, sys_id, ci["id"], verification_result.result["status"], planner_result.result))
        trace.append(sync_result)
        write_audit_entry(conn, actor="agent:sync", action="sync_outcome", target_artifact=incident_id, evidence_ids=sync_result.cited_artifact_ids)

        knowledge_result = await _timed(run_knowledge(
            incident_id, ci["type"], verification_result.result["status"],
            failure_signature=top_hypothesis["text"], attempted_fix=planner_result.result.get("runbook_id", ""),
        ))
        trace.append(knowledge_result)
        write_audit_entry(conn, actor="agent:knowledge", action="capture_outcome", target_artifact=incident_id)

        return {"status": "complete", "verification_status": verification_result.result["status"], "trace": trace, "sys_id": sys_id}
    finally:
        conn.close()
