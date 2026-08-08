"""Unit tests for the maintenance-window scheduling rule engine against hand-built fixtures (not
the randomized generated data — fixed inputs with a hand-verifiable expected answer)."""
from datetime import datetime, timedelta, timezone

from guardrails.scheduling import propose_maintenance_window

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _patch(id_, severity, released_days_ago=0, sla_days=30, depends_on=None):
    return {
        "id": id_, "ci_id": "CI-X", "severity": severity,
        "released_at": (NOW - timedelta(days=released_days_ago)).isoformat(),
        "sla_days": sla_days, "depends_on_patch_ids": depends_on or [],
    }


def test_no_pending_patches_returns_no_window():
    result = propose_maintenance_window("CI-X", "prod", [], [], now=NOW)
    assert result["proposed_window"] is None
    assert result["grouped_patches"] == []
    assert result["sla_at_risk"] is False


def test_empty_calendar_proposes_window_starting_now():
    patches = [_patch("P1", "high")]
    result = propose_maintenance_window("CI-X", "prod", patches, [], now=NOW)
    assert result["proposed_window"]["start"] == NOW.isoformat()
    assert result["blackout_windows_checked"] == 0


def test_dependency_order_respected_even_when_severity_would_reorder():
    # P2 (critical) depends on P1 (low) — dependency wins, P1 must still come first.
    patches = [_patch("P2", "critical", depends_on=["P1"]), _patch("P1", "low")]
    result = propose_maintenance_window("CI-X", "prod", patches, [], now=NOW)
    order = [p["id"] for p in result["grouped_patches"]]
    assert order == ["P1", "P2"]


def test_severity_breaks_ties_among_independent_patches():
    patches = [_patch("P1", "low"), _patch("P2", "critical"), _patch("P3", "medium")]
    result = propose_maintenance_window("CI-X", "prod", patches, [], now=NOW)
    order = [p["id"] for p in result["grouped_patches"]]
    assert order == ["P2", "P3", "P1"]


def test_global_blackout_pushes_window_past_its_end():
    patches = [_patch("P1", "high")]
    calendar = [{"id": "B1", "scope": "global", "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(hours=5)).isoformat(), "reason": "freeze"}]
    result = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW, window_hours=2)
    start = datetime.fromisoformat(result["proposed_window"]["start"])
    assert start == NOW + timedelta(hours=5)


def test_environment_scoped_blackout_applies_but_other_environment_does_not():
    patches = [_patch("P1", "high")]
    calendar = [{"id": "B1", "scope": "staging", "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(hours=5)).isoformat(), "reason": "freeze"}]
    prod_result = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW, window_hours=2)
    staging_result = propose_maintenance_window("CI-X", "staging", patches, calendar, now=NOW, window_hours=2)
    assert prod_result["proposed_window"]["start"] == NOW.isoformat()  # unaffected
    assert datetime.fromisoformat(staging_result["proposed_window"]["start"]) == NOW + timedelta(hours=5)


def test_ci_scoped_blackout_applies_only_to_that_ci():
    patches = [_patch("P1", "high")]
    calendar = [{"id": "B1", "scope": "CI-OTHER", "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(hours=5)).isoformat(), "reason": "freeze"}]
    result = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW, window_hours=2)
    assert result["proposed_window"]["start"] == NOW.isoformat()  # blackout scoped to a different CI


def test_sla_at_risk_flagged_when_proposed_window_is_after_the_deadline():
    # Released 29 days ago with a 30-day SLA -> due in 1 day; a 5h blackout starting now still
    # pushes the window past "now" but not past the 1-day deadline, so this should NOT be at risk...
    patches = [_patch("P1", "critical", released_days_ago=29, sla_days=30)]
    calendar = [{"id": "B1", "scope": "global", "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(days=2)).isoformat(), "reason": "freeze"}]
    # ...but here the blackout runs 2 days, past the 1-day-away SLA deadline -> should be at risk.
    result = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW, window_hours=2)
    assert result["sla_at_risk"] is True
    assert result["earliest_sla_due"] == (NOW - timedelta(days=29) + timedelta(days=30)).isoformat()


def test_sla_not_at_risk_when_window_lands_before_deadline():
    patches = [_patch("P1", "low", released_days_ago=1, sla_days=60)]
    result = propose_maintenance_window("CI-X", "prod", patches, [], now=NOW)
    assert result["sla_at_risk"] is False


def test_deterministic_same_input_same_output():
    patches = [_patch("P1", "high"), _patch("P2", "critical")]
    calendar = [{"id": "B1", "scope": "global", "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(hours=3)).isoformat(), "reason": "freeze"}]
    r1 = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW)
    r2 = propose_maintenance_window("CI-X", "prod", patches, calendar, now=NOW)
    assert r1 == r2
