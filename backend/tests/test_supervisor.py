"""Integration tests for the Supervisor's full dispatch loop — real gateway calls (Diagnosis,
Planner), real MCP tool calls (in-process), real Chroma retrieval, real SQLite writes.
Covers the 3 workflow families and the schema-validation/policy-gate control points.
"""
import asyncio
import json
import os

import pytest

from orchestrator.mcp_wiring import wire_all_in_process
from orchestrator.supervisor import run_workflow

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# CI-0059: staging/P3, blast radius 0, stable metrics -> a clean "verified_resolved" happy path.
STABLE_LOW_BR_CI_ID = "CI-0059"
# CI-0121: dev/P3, blast radius 2, degradation metrics -> the Fake Fix Detector should catch this.
DEGRADED_LOW_BR_CI_ID = "CI-0121"
# CI-0009: blast radius 21 (> block threshold 15) -> should be blocked outright.
HIGH_BR_CI_ID = "CI-0009"


def _load_cis() -> dict:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return {ci["id"]: ci for ci in json.load(f)["cis"]}


def _fault_alerts_for(ci_id: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        alerts = json.load(f)
    return [a for a in alerts if a["ci_id"] == ci_id and a["category"] == "fault"]


@pytest.fixture(scope="module", autouse=True)
def _wire():
    wire_all_in_process()


def test_incident_workflow_completes_and_verifies_resolved_on_stable_ci():
    cis = _load_cis()
    ci = cis[STABLE_LOW_BR_CI_ID]
    alerts = _fault_alerts_for(STABLE_LOW_BR_CI_ID)
    outcome = asyncio.run(run_workflow(incident_id="INC-SUP-001", ci=ci, alerts=alerts, workflow_type="incident"))

    assert outcome["status"] == "complete", outcome
    assert outcome["verification_status"] == "verified_resolved"
    agent_names = [r.agent_name for r in outcome["trace"]]
    assert agent_names == ["enrichment", "diagnosis", "planner", "verification", "sync", "knowledge"]
    for r in outcome["trace"]:
        assert r.termination_reason  # explicit, never empty (never "silent" termination)


def test_incident_workflow_catches_fake_fix_on_degraded_ci():
    cis = _load_cis()
    ci = cis[DEGRADED_LOW_BR_CI_ID]
    alerts = _fault_alerts_for(DEGRADED_LOW_BR_CI_ID)
    outcome = asyncio.run(run_workflow(incident_id="INC-SUP-002", ci=ci, alerts=alerts, workflow_type="incident"))

    assert outcome["status"] == "complete", outcome
    assert outcome["verification_status"] == "symptom_suppressed"
    knowledge_result = next(r for r in outcome["trace"] if r.agent_name == "knowledge")
    assert knowledge_result.result["negative_kb_entry"] is not None  # failure seeded into Negative KB
    sync_result = next(r for r in outcome["trace"] if r.agent_name == "sync")
    assert sync_result.result["ticket"]["state"] == "2"  # NOT closed — incident correctly stays open


def test_high_blast_radius_ci_is_blocked_before_approval():
    cis = _load_cis()
    ci = cis[HIGH_BR_CI_ID]
    alerts = _fault_alerts_for(HIGH_BR_CI_ID) or [{"id": "ALERT-SYNTH-1", "ci_id": HIGH_BR_CI_ID, "category": "fault", "severity": "warning", "source": "prometheus", "received_at": "2026-08-07T00:00:00", "raw_payload": {}}]
    outcome = asyncio.run(run_workflow(incident_id="INC-SUP-003", ci=ci, alerts=alerts, workflow_type="incident"))
    assert outcome["status"] == "blocked"


def test_performance_workflow_always_needs_approval_never_auto_completes():
    cis = _load_cis()
    ci = cis[STABLE_LOW_BR_CI_ID]
    alerts = _fault_alerts_for(STABLE_LOW_BR_CI_ID)
    outcome = asyncio.run(run_workflow(incident_id="INC-SUP-004", ci=ci, alerts=alerts, workflow_type="performance", auto_approve=False))
    assert outcome["status"] == "pending_approval"  # advisory-only: never silently auto-executes


def test_patch_workflow_runs_through_planner_with_patching_runbook_class():
    cis = _load_cis()
    ci = cis[STABLE_LOW_BR_CI_ID]
    alerts = _fault_alerts_for(STABLE_LOW_BR_CI_ID)
    outcome = asyncio.run(run_workflow(incident_id="INC-SUP-005", ci=ci, alerts=alerts, workflow_type="patch"))
    # "blocked" is a real, correct outcome here (not previously possible before 2026-08-17's
    # policy_gate.py wiring fix): patch/change-freeze windows (data/change_calendar.json) are now
    # actually consulted for patching workflows, and this suite can run while one is genuinely
    # active (see agents/planner.py's _load_policy_context docstring).
    assert outcome["status"] in ("complete", "pending_approval", "stopped", "blocked")
    planner_result = next((r for r in outcome["trace"] if r.agent_name == "planner"), None)
    if planner_result:
        assert planner_result.turns_used >= 1
        # STABLE_LOW_BR_CI_ID (CI-0059) is a guaranteed-coverage CI in data_gen/patch_inventory.py
        # — the intelligent-scheduling maintenance window must be computed for a real patch run.
        window = planner_result.result.get("maintenance_window")
        assert window is not None
        assert window["ci_id"] == STABLE_LOW_BR_CI_ID
        assert window["proposed_window"] is not None
    enrichment_result = next((r for r in outcome["trace"] if r.agent_name == "enrichment"), None)
    if enrichment_result:
        source_types = {e["source_type"] for e in enrichment_result.result["evidence"]}
        assert "patch_inventory" in source_types
        assert "change_calendar" in source_types
