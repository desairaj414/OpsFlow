"""Tests for the A2A handoff (Supervisor -> Diagnosis): signed Agent Card, discovery, and
invocation over the A2A endpoint (in-process ASGI transport)."""
import asyncio

from a2a.agent_card import DIAGNOSIS_AGENT_CARD, build_agent_card, verify_agent_card
from a2a.client import fetch_agent_card, invoke_diagnosis_via_a2a, wire_in_process

SAMPLE_EVIDENCE = [
    {"artifact_id": "CI-0009", "source_type": "cmdb", "extract": "db-server in dev, criticality P4"},
    {"artifact_id": "ALERT-0001", "source_type": "alert", "extract": "connection refused"},
]


def test_agent_card_signature_is_valid():
    assert verify_agent_card(DIAGNOSIS_AGENT_CARD) is True


def test_agent_card_tampering_is_detected():
    tampered = dict(DIAGNOSIS_AGENT_CARD)
    tampered["capabilities"] = ["generate_diagnosis", "auto_execute"]  # a fabricated extra capability
    assert verify_agent_card(tampered) is False


def test_agent_card_has_required_fields():
    for field in ("name", "description", "capabilities", "endpoint", "signature"):
        assert field in DIAGNOSIS_AGENT_CARD


def test_discovery_endpoint_returns_the_signed_card():
    wire_in_process()
    card = asyncio.run(fetch_agent_card())
    assert card == DIAGNOSIS_AGENT_CARD
    assert verify_agent_card(card) is True


def test_invoke_over_a2a_returns_valid_specialist_result():
    wire_in_process()
    result = asyncio.run(invoke_diagnosis_via_a2a(incident_id="INC-A2A-TEST-1", evidence=SAMPLE_EVIDENCE))
    assert result.agent_name == "diagnosis"
    assert result.incident_id == "INC-A2A-TEST-1"
    assert result.termination_reason in ("hypotheses_generated", "no_valid_hypotheses")


def test_build_agent_card_produces_verifiable_signature_for_any_card():
    card = build_agent_card(name="test-agent", description="test", capabilities=["x"], endpoint="http://localhost:1/invoke")
    assert verify_agent_card(card) is True
