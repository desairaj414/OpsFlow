"""Unit test for the Enrichment agent, against the in-process-wired simulators (real MCP tool
calls, real Chroma retrieval — the only thing not "real" here is the network hop)."""
import asyncio
import json
import os

from agents.enrichment import run_enrichment
from orchestrator.mcp_wiring import wire_all_in_process

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _sample_alert_and_ci() -> tuple[str, list[dict]]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        alerts = json.load(f)
    fault_alerts = [a for a in alerts if a["category"] == "fault"]
    ci_id = fault_alerts[0]["ci_id"]
    matching = [a for a in fault_alerts if a["ci_id"] == ci_id][:2]
    return ci_id, matching


def test_enrichment_gathers_ci_and_alert_evidence():
    wire_all_in_process()
    ci_id, alerts = _sample_alert_and_ci()
    result = asyncio.run(run_enrichment(incident_id="INC-TEST-001", ci_id=ci_id, alerts=alerts))

    assert result.agent_name == "enrichment"
    assert result.termination_reason == "evidence_gathering_complete"
    assert ci_id in result.cited_artifact_ids
    for alert in alerts:
        assert alert["id"] in result.cited_artifact_ids
    assert len(result.result["evidence"]) >= len(alerts) + 1  # CI fact + each alert, at minimum
    assert result.turns_used <= 3  # matches TURN_CAPS["enrichment"]


def test_enrichment_respects_turn_cap_registration():
    from orchestrator.limits import TURN_CAPS
    assert "enrichment" in TURN_CAPS


def test_enrichment_evidence_extracts_are_truncated():
    wire_all_in_process()
    ci_id, alerts = _sample_alert_and_ci()
    result = asyncio.run(run_enrichment(incident_id="INC-TEST-002", ci_id=ci_id, alerts=alerts))
    for item in result.result["evidence"]:
        assert len(item["extract"]) <= 300  # generous bound above _EXTRACT_MAX_CHARS to allow prefixes


def test_patch_workflow_gathers_patch_inventory_and_change_calendar_evidence():
    # CI-0059 is a guaranteed-coverage CI in data_gen/patch_inventory.py — always has pending
    # patches and a dedicated blackout window, so this test isn't at the mercy of random coverage.
    wire_all_in_process()
    result = asyncio.run(run_enrichment(incident_id="INC-TEST-003", ci_id="CI-0059", alerts=[], workflow_type="patch"))
    source_types = {e["source_type"] for e in result.result["evidence"]}
    assert "patch_inventory" in source_types
    assert "change_calendar" in source_types
    assert "PATCHINV-CI-0059" in result.cited_artifact_ids
    assert result.turns_used <= 3  # folded into turn 1's budget, not a 4th turn — matches TURN_CAPS["enrichment"]


def test_incident_workflow_does_not_gather_patch_evidence():
    # workflow_type default ("incident") must NOT pull patch/change-calendar evidence — parity
    # table scopes that evidence to Patch Management only.
    wire_all_in_process()
    result = asyncio.run(run_enrichment(incident_id="INC-TEST-004", ci_id="CI-0059", alerts=[]))
    source_types = {e["source_type"] for e in result.result["evidence"]}
    assert "patch_inventory" not in source_types
    assert "change_calendar" not in source_types
