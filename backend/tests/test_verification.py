"""Unit tests for the Verification agent (Fake Fix Detector) against real Phase 1 metric data —
a degradation-curve CI (tail still high) is the deliberately-rigged "alert cleared but root cause
unconfirmed" fixture required by prd-phase-3.md's acceptance criteria."""
import asyncio
import csv
import json
import os

from agents.verification import STATUS_NOT_YET_RESOLVED, STATUS_SYMPTOM_SUPPRESSED, STATUS_VERIFIED_RESOLVED, run_verification

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_series(ci_id: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, "metrics", f"{ci_id}.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _degradation_and_stable_ci_ids() -> tuple[str, str]:
    with open(os.path.join(DATA_DIR, "metrics_index.json"), encoding="utf-8") as f:
        index = json.load(f)
    degradation_id = index["degradation_ci_ids"][0]
    stable_id = next(ci for ci in index["sampled_ci_ids"] if ci not in index["degradation_ci_ids"])
    return degradation_id, stable_id


def test_alert_cleared_but_metric_never_recovered_is_symptom_suppressed():
    """The deliberately-rigged fixture: alert says fixed, but the tail of the metric series is
    still degraded — the real signature of a fake fix (e.g. a restart that masked the symptom)."""
    degradation_ci, _ = _degradation_and_stable_ci_ids()
    series = _load_series(degradation_ci)  # tail stays high by construction (data_gen/metrics.py)
    result = asyncio.run(run_verification(incident_id="INC-TEST-VER-1", alert_cleared=True, metric_series=series, metric_key="memory_pct", baseline_threshold=66.0))
    assert result.result["status"] == STATUS_SYMPTOM_SUPPRESSED
    assert result.result["alert_cleared"] is True
    assert result.result["health_probe_recovered"] is False


def test_alert_cleared_and_metric_stable_is_verified_resolved():
    _, stable_ci = _degradation_and_stable_ci_ids()
    series = _load_series(stable_ci)  # jitters around baseline, never exceeds threshold
    result = asyncio.run(run_verification(incident_id="INC-TEST-VER-2", alert_cleared=True, metric_series=series, metric_key="memory_pct", baseline_threshold=66.0))
    assert result.result["status"] == STATUS_VERIFIED_RESOLVED
    assert result.result["health_probe_recovered"] is True


def test_alert_not_cleared_is_not_yet_resolved_regardless_of_metrics():
    _, stable_ci = _degradation_and_stable_ci_ids()
    series = _load_series(stable_ci)
    result = asyncio.run(run_verification(incident_id="INC-TEST-VER-3", alert_cleared=False, metric_series=series))
    assert result.result["status"] == STATUS_NOT_YET_RESOLVED


def test_single_improved_point_is_not_sufficient():
    """A single good reading at the very end, preceded by a still-bad tail, must NOT verify —
    'sustained' means the whole tail window, not the last point."""
    mostly_bad_then_one_good = [{"memory_pct": "90"}] * 9 + [{"memory_pct": "10"}]
    result = asyncio.run(run_verification(incident_id="INC-TEST-VER-4", alert_cleared=True, metric_series=mostly_bad_then_one_good, metric_key="memory_pct", baseline_threshold=66.0))
    assert result.result["status"] == STATUS_SYMPTOM_SUPPRESSED


def test_no_metric_series_provided_cannot_verify():
    result = asyncio.run(run_verification(incident_id="INC-TEST-VER-5", alert_cleared=True, metric_series=None))
    assert result.result["status"] == STATUS_SYMPTOM_SUPPRESSED
    assert result.result["health_probe_recovered"] is False
