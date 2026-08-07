"""Verification agent — the Fake Fix Detector (domain-guardrails.md pillar (a), anti-reward-hacking).
Deterministic, no LLM. Requires TWO independent signals: alert cleared AND the underlying
metric/health probe recovered and HELD through a stabilisation window — a single improved data
point is not sufficient. If only the alert cleared, marks `symptom_suppressed,
root_cause_unconfirmed` and keeps the incident open, rather than trusting the alert alone
(ITBench: 44% of "solved" mitigation problems were a generic restart loop with no real fix).

"Held through the stabilisation window" is checked against the TAIL of the post-fix metric
series (not a single point) — this agent does not itself wait in real time; the caller supplies
the metric series covering the window to check.
"""
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TurnTracker

STATUS_VERIFIED_RESOLVED = "verified_resolved"
STATUS_SYMPTOM_SUPPRESSED = "symptom_suppressed"
STATUS_NOT_YET_RESOLVED = "not_yet_resolved"

DEFAULT_TAIL_FRACTION = 0.3


def _held_through_stabilisation_window(series: list[dict], metric_key: str, baseline_threshold: float, tail_fraction: float = DEFAULT_TAIL_FRACTION) -> bool:
    if not series:
        return False
    tail_size = max(1, int(len(series) * tail_fraction))
    tail = series[-tail_size:]
    return all(float(pt[metric_key]) <= baseline_threshold for pt in tail)


async def run_verification(
    incident_id: str,
    alert_cleared: bool,
    metric_series: list[dict] | None = None,
    metric_key: str = "memory_pct",
    baseline_threshold: float = 60.0,
) -> SpecialistResult:
    tracker = TurnTracker("verification")
    tracker.use_turn()

    health_probe_recovered = _held_through_stabilisation_window(metric_series or [], metric_key, baseline_threshold)

    if not alert_cleared:
        status = STATUS_NOT_YET_RESOLVED
    elif health_probe_recovered:
        status = STATUS_VERIFIED_RESOLVED
    else:
        status = STATUS_SYMPTOM_SUPPRESSED

    return SpecialistResult(
        agent_name="verification", incident_id=incident_id,
        result={
            "alert_cleared": alert_cleared,
            "health_probe_recovered": health_probe_recovered,
            "status": status,
        },
        cited_artifact_ids=[],  # a verdict on measurements, not a claim needing artifact citation
        confidence=1.0,  # deterministic check, not a probabilistic judgement
        turns_used=tracker.turns_used, termination_reason="verification_complete",
    )
