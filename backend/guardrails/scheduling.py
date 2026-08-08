"""Maintenance-window scheduling for Patch Management (PRD clause C6: "intelligent scheduling —
dependency-aware, blackout-aware, SLA-aware") — pure Python rule engine, no LLM, same category as
blast_radius.py and policy_gate.py (PRD line 482: "Policy gate, blast radius, scheduling
constraints ... No LLM — rule engine ... must be auditable and provably consistent"). Called from
agents/planner.py only when runbook_class == 'patching'; produces the parity table's
`grouped_maintenance_window` plan_output (domain-workflows.md).
"""
from datetime import datetime, timedelta, timezone

DEFAULT_WINDOW_HOURS = 2
SEARCH_STEP_LIMIT = 2000  # bounds the blackout-avoidance search; generated data has <20 windows
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _dependency_and_severity_order(patches: list[dict]) -> list[dict]:
    """A patch always sorts after every patch it depends_on (same CI); among patches that are
    currently ready, higher severity goes first. Deterministic tie-break by id."""
    by_id = {p["id"]: p for p in patches}
    ordered: list[dict] = []
    placed: set[str] = set()
    remaining = list(patches)
    while remaining:
        ready = [
            p for p in remaining
            if all(dep in placed or dep not in by_id for dep in p.get("depends_on_patch_ids", []))
        ]
        if not ready:
            ready = remaining  # dependency cycle in malformed input — never hang, just proceed
        ready.sort(key=lambda p: (SEVERITY_ORDER.get(p["severity"], 9), p["id"]))
        chosen = ready[0]
        ordered.append(chosen)
        placed.add(chosen["id"])
        remaining.remove(chosen)
    return ordered


def _earliest_sla_due(patches: list[dict]) -> datetime | None:
    due_dates = [
        datetime.fromisoformat(p["released_at"]) + timedelta(days=p["sla_days"])
        for p in patches
    ]
    return min(due_dates) if due_dates else None


def _applicable_blackouts(change_calendar: list[dict], environment: str, ci_id: str) -> list[dict]:
    return [w for w in change_calendar if w["scope"] in ("global", environment, ci_id)]


def _overlaps(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> bool:
    return start < window_end and end > window_start


def _find_open_slot(search_from: datetime, blackouts: list[dict], window_hours: int) -> tuple[datetime, datetime]:
    """Earliest window_hours-long slot starting at/after search_from that overlaps no blackout.
    Blackouts sorted by start; whenever the candidate slot collides, jump straight to that
    blackout's end and retry — bounded, never a per-minute scan."""
    parsed = sorted(
        (datetime.fromisoformat(w["starts_at"]), datetime.fromisoformat(w["ends_at"]))
        for w in blackouts
    )
    candidate = search_from
    for _ in range(SEARCH_STEP_LIMIT):
        candidate_end = candidate + timedelta(hours=window_hours)
        conflict_end = next((end for start, end in parsed if _overlaps(candidate, candidate_end, start, end)), None)
        if conflict_end is None:
            return candidate, candidate_end
        candidate = conflict_end
    return candidate, candidate + timedelta(hours=window_hours)


def propose_maintenance_window(
    ci_id: str, environment: str, pending_patches: list[dict], change_calendar: list[dict],
    now: datetime | None = None, window_hours: int = DEFAULT_WINDOW_HOURS,
) -> dict:
    """Deterministic: same inputs always produce the same proposed window (auditable per PRD)."""
    if not pending_patches:
        return {
            "ci_id": ci_id, "grouped_patches": [], "proposed_window": None,
            "sla_at_risk": False, "earliest_sla_due": None, "blackout_windows_checked": 0,
        }

    now = now or datetime.now(timezone.utc)
    grouped = _dependency_and_severity_order(pending_patches)
    blackouts = _applicable_blackouts(change_calendar, environment, ci_id)
    window_start, window_end = _find_open_slot(now, blackouts, window_hours)
    earliest_due = _earliest_sla_due(pending_patches)

    return {
        "ci_id": ci_id,
        "grouped_patches": [
            {"id": p["id"], "severity": p["severity"], "order": i + 1, "depends_on_patch_ids": p.get("depends_on_patch_ids", [])}
            for i, p in enumerate(grouped)
        ],
        "proposed_window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "sla_at_risk": earliest_due is not None and window_start > earliest_due,
        "earliest_sla_due": earliest_due.isoformat() if earliest_due else None,
        "blackout_windows_checked": len(blackouts),
    }
