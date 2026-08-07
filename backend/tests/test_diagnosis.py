"""Unit tests for the Diagnosis agent — real DeepSeek R1 calls against the gateway. Citation
enforcement is tested both against the real model and with a hand-crafted fixture that would be
wrong if citation filtering weren't applied.
"""
import asyncio

from agents.diagnosis import _parse_and_filter, run_diagnosis

SAMPLE_EVIDENCE = [
    {"artifact_id": "CI-0009", "source_type": "cmdb", "extract": "db-server in dev, criticality P4, patch_level 3.1.2"},
    {"artifact_id": "ALERT-0001", "source_type": "alert", "extract": "[prometheus/fault/warning] connection refused on db-server"},
    {"artifact_id": "METRICS-CI-0009", "source_type": "metrics", "extract": "degradation trend: memory 40%->78%, latency 90ms->520ms"},
]


def test_diagnosis_produces_cited_hypotheses_against_real_gateway():
    result = asyncio.run(run_diagnosis(incident_id="INC-TEST-DIAG-1", evidence=SAMPLE_EVIDENCE))
    assert result.agent_name == "diagnosis"
    assert result.termination_reason in ("hypotheses_generated", "no_valid_hypotheses")
    if result.termination_reason == "hypotheses_generated":
        assert len(result.result["hypotheses"]) >= 1
        for h in result.result["hypotheses"]:
            assert len(h["cited_artifact_ids"]) > 0
            assert set(h["cited_artifact_ids"]).issubset({e["artifact_id"] for e in SAMPLE_EVIDENCE})
        # sorted descending by confidence
        confidences = [h["confidence"] for h in result.result["hypotheses"]]
        assert confidences == sorted(confidences, reverse=True)
    assert result.turns_used <= 3


def test_citation_enforcement_drops_uncited_hypothesis():
    valid_ids = {"CI-0009", "ALERT-0001"}
    raw = '{"hypotheses": [{"text": "no citation here", "confidence": 0.9, "cited_artifact_ids": []}]}'
    surviving = _parse_and_filter(raw, valid_ids)
    assert surviving == []


def test_citation_enforcement_drops_hallucinated_artifact_id():
    valid_ids = {"CI-0009", "ALERT-0001"}
    raw = '{"hypotheses": [{"text": "cites something fake", "confidence": 0.9, "cited_artifact_ids": ["CI-9999-FAKE"]}]}'
    surviving = _parse_and_filter(raw, valid_ids)
    assert surviving == []


def test_citation_enforcement_keeps_validly_cited_hypothesis():
    valid_ids = {"CI-0009", "ALERT-0001"}
    raw = '{"hypotheses": [{"text": "valid", "confidence": 0.7, "cited_artifact_ids": ["CI-0009"]}]}'
    surviving = _parse_and_filter(raw, valid_ids)
    assert len(surviving) == 1
    assert surviving[0]["cited_artifact_ids"] == ["CI-0009"]


def test_mixed_batch_keeps_only_validly_cited():
    valid_ids = {"CI-0009", "ALERT-0001"}
    raw = (
        '{"hypotheses": ['
        '{"text": "bad - no citation", "confidence": 0.9, "cited_artifact_ids": []},'
        '{"text": "bad - fake citation", "confidence": 0.8, "cited_artifact_ids": ["FAKE-1"]},'
        '{"text": "good", "confidence": 0.5, "cited_artifact_ids": ["ALERT-0001"]}'
        ']}'
    )
    surviving = _parse_and_filter(raw, valid_ids)
    assert len(surviving) == 1
    assert surviving[0]["text"] == "good"
