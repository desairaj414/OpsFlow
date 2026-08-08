"""Generates a large historical ticket backlog for the Tickets tab — separate from tickets.csv on
purpose. tickets.csv feeds the `ticket_history` Chroma collection (real gateway embedding calls,
one per row); scaling THAT to thousands of rows would mean thousands of real embedding calls for
data whose only job is to make the Tickets tab look like a populated system of record. This
generator produces db/init_db.py's `local_tickets` rows directly — zero gateway cost, instant to
rebuild. Historical/pre-session data, same convention as populate_tracker_backlog's Jira seed: a
minimal placeholder trace_snapshot, since these were never run through the agent chain.

    python data_gen/local_tickets_bulk.py

Writes:
    data/local_tickets_seed.json   TOTAL_PER_SYSTEM rows for 'itsm' + TOTAL_PER_SYSTEM for 'tracker',
                                    each system split as evenly as possible across
                                    incident / patch / performance.
"""
import json
import os
import random
from datetime import datetime, timedelta, timezone

SEED = 20260807
random.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

TOTAL_PER_SYSTEM = 2000
WORKFLOW_TYPES = ["incident", "patch", "performance"]

PRIORITIES = ["P1", "P2", "P3", "P4"]

SUMMARY_POOL = {
    "incident": [
        "Service outage on {ci}", "Elevated error rate on {ci}", "{ci} health check failing",
        "Connection timeouts to {ci}", "Authentication failures against {ci}",
    ],
    "patch": [
        "Vendor security patch pending for {ci}", "Scheduled patch window for {ci}",
        "Critical CVE remediation for {ci}", "Quarterly patch compliance pass for {ci}",
    ],
    "performance": [
        "Latency tuning investigation for {ci}", "Memory usage tuning for {ci}",
        "Query optimisation review for {ci}", "Throughput degradation on {ci}",
    ],
}

# ServiceNow state names vs. Jira status names — kept distinct so status_raw still reads as
# authentic per system even though status_normalized (what the UI actually keys off) is shared.
ITSM_STATUS = [("Resolved", "resolved", 0.68), ("In Progress", "in_progress", 0.16), ("New", "open", 0.16)]
TRACKER_STATUS = [("Done", "resolved", 0.68), ("In Progress", "in_progress", 0.16), ("Open", "open", 0.16)]


def _load_ci_ids() -> list[str]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return [ci["id"] for ci in json.load(f)["cis"]]


def _weighted_status(pool: list[tuple[str, str, float]]) -> tuple[str, str]:
    r = random.random()
    cumulative = 0.0
    for raw, normalized, weight in pool:
        cumulative += weight
        if r <= cumulative:
            return raw, normalized
    return pool[-1][0], pool[-1][1]


def _even_workflow_types(n: int) -> list[str]:
    """Round-robin, not random sampling — guarantees an exact (or off-by-one) even split rather
    than an approximate one, since "divided equally" was an explicit ask."""
    return [WORKFLOW_TYPES[i % len(WORKFLOW_TYPES)] for i in range(n)]


def generate_system(system: str, id_prefix: str, status_pool: list[tuple[str, str, float]], ci_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    workflow_types = _even_workflow_types(TOTAL_PER_SYSTEM)
    random.shuffle(workflow_types)  # even split, but not grouped in one visible block
    rows = []
    for i in range(1, TOTAL_PER_SYSTEM + 1):
        wf = workflow_types[i - 1]
        ci_id = random.choice(ci_ids)
        status_raw, status_normalized = _weighted_status(status_pool)
        opened = now - timedelta(days=random.randint(1, 180), hours=random.randint(0, 23))
        closed = opened + timedelta(hours=random.uniform(0.5, 96)) if status_normalized == "resolved" else None
        external_id = f"INC{1000000 + i:07d}" if system == "itsm" else f"OPS-{i}"
        rows.append({
            "system": system,
            "external_id": external_id,
            "cmdb_ci": ci_id,
            "workflow_type": wf,
            "status_raw": status_raw,
            "status_normalized": status_normalized,
            "priority": random.choice(PRIORITIES),
            "summary": random.choice(SUMMARY_POOL[wf]).format(ci=ci_id),
            "opened_at": opened.isoformat(),
            "closed_at": closed.isoformat() if closed else None,
        })
    return rows


def main() -> None:
    ci_ids = _load_ci_ids()
    rows = generate_system("itsm", "INC", ITSM_STATUS, ci_ids) + generate_system("tracker", "OPS", TRACKER_STATUS, ci_ids)
    with open(os.path.join(DATA_DIR, "local_tickets_seed.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    by_system = {s: sum(1 for r in rows if r["system"] == s) for s in ("itsm", "tracker")}
    by_wf = {w: sum(1 for r in rows if r["workflow_type"] == w) for w in WORKFLOW_TYPES}
    print(f"local_tickets_seed.json: {len(rows)} rows, by system={by_system}, by workflow_type={by_wf}")


if __name__ == "__main__":
    main()

    with open(os.path.join(DATA_DIR, "local_tickets_seed.json"), encoding="utf-8") as f:
        rows = json.load(f)
    assert len(rows) == TOTAL_PER_SYSTEM * 2
    by_system = {}
    by_system_wf = {}
    for r in rows:
        by_system[r["system"]] = by_system.get(r["system"], 0) + 1
        by_system_wf.setdefault(r["system"], {}).setdefault(r["workflow_type"], 0)
        by_system_wf[r["system"]][r["workflow_type"]] += 1
    assert by_system == {"itsm": TOTAL_PER_SYSTEM, "tracker": TOTAL_PER_SYSTEM}
    for system, counts in by_system_wf.items():
        assert set(counts) == set(WORKFLOW_TYPES), f"{system} missing a workflow type"
        assert max(counts.values()) - min(counts.values()) <= 1, f"{system} workflow types not evenly split: {counts}"
    ext_ids = {r["external_id"] for r in rows}
    assert len(ext_ids) == len(rows), "duplicate external_id"
    ci_ids_set = set(_load_ci_ids())
    assert all(r["cmdb_ci"] in ci_ids_set for r in rows), "a row references a CI not in cmdb.json"
    print(f"\nSELF-TEST PASSED: {len(rows)} rows, even system totals, even per-system workflow-type split, "
          f"unique external ids, all CI references valid.")
