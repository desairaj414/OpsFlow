"""Unit tests for the Planner agent — real gpt-4.1-nano calls + real Chroma runbook retrieval,
scoped to the workflow's runbook class (runbook-bounded action space)."""
import asyncio

from agents.planner import _parse_and_filter_steps, run_planner
from orchestrator.mcp_wiring import wire_all_in_process

SAMPLE_CI = {"id": "CI-0009", "type": "db-server", "environment": "staging", "criticality": "P3"}
SAMPLE_HYPOTHESIS = {"text": "db-server memory exhaustion causing connection refusal", "confidence": 0.7, "cited_artifact_ids": ["CI-0009"]}
# CI-0059 is a guaranteed-coverage CI in data_gen/patch_inventory.py — always has pending patches.
PATCH_CI = {"id": "CI-0059", "type": "sharepoint-site", "environment": "prod", "criticality": "P3"}


def test_planner_drafts_bounded_plan_against_real_gateway():
    result = asyncio.run(run_planner(incident_id="INC-TEST-PLAN-1", ci=SAMPLE_CI, runbook_class="remediation", hypothesis=SAMPLE_HYPOTHESIS))
    assert result.agent_name == "planner"
    assert result.termination_reason in ("plan_drafted", "no_valid_runbook_found")
    assert "blast_radius" in result.result
    assert "policy_gate_result" in result.result
    assert result.result["policy_gate_result"]["decision"] in ("allow", "needs_approval", "block")
    if result.termination_reason == "plan_drafted":
        assert len(result.result["steps"]) >= 1
        for step in result.result["steps"]:
            assert step["cites_runbook_step"] in result.cited_artifact_ids


def test_tuning_runbook_class_never_reaches_allow():
    """Cross-checks Phase 2's advisory-only-tuning rule is actually wired in here, not just present
    in isolation. CI-0009's real blast radius (21, > block threshold 15) additionally triggers a
    hard block here — both rules stacking is correct; the invariant under test is just that tuning
    never silently reaches 'allow', regardless of which other rule also fires."""
    result = asyncio.run(run_planner(incident_id="INC-TEST-PLAN-2", ci=SAMPLE_CI, runbook_class="tuning", hypothesis=SAMPLE_HYPOTHESIS))
    assert result.result["policy_gate_result"]["decision"] != "allow"
    assert "ADVISORY_ONLY_WORKFLOW" in result.result["policy_gate_result"]["triggered_rules"]


def test_step_bounded_to_retrieved_chunks_drops_hallucinated_citation():
    raw = '{"runbook_id": "RB-001", "steps": [{"step_no": 1, "action": "invented step", "cites_runbook_step": "RB-999-FAKE"}]}'
    result = _parse_and_filter_steps(raw, {"RB-001-step1", "RB-001-step2"})
    assert result["steps"] == []


def test_step_bounded_to_retrieved_chunks_keeps_valid_citation():
    raw = '{"runbook_id": "RB-001", "steps": [{"step_no": 1, "action": "real step", "cites_runbook_step": "RB-001-step1"}]}'
    result = _parse_and_filter_steps(raw, {"RB-001-step1", "RB-001-step2"})
    assert len(result["steps"]) == 1


def test_patching_runbook_class_computes_maintenance_window():
    wire_all_in_process()
    result = asyncio.run(run_planner(incident_id="INC-TEST-PLAN-3", ci=PATCH_CI, runbook_class="patching", hypothesis=SAMPLE_HYPOTHESIS))
    window = result.result.get("maintenance_window")
    assert window is not None, "CI-0059 always has pending patches (guaranteed-coverage), maintenance_window must be computed"
    assert window["ci_id"] == "CI-0059"
    assert len(window["grouped_patches"]) >= 1
    assert window["proposed_window"] is not None
    assert "sla_at_risk" in window


def test_non_patching_runbook_class_has_no_maintenance_window():
    result = asyncio.run(run_planner(incident_id="INC-TEST-PLAN-4", ci=SAMPLE_CI, runbook_class="remediation", hypothesis=SAMPLE_HYPOTHESIS))
    assert "maintenance_window" not in result.result
