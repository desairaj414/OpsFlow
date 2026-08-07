"""Generates ITSM-adjacent history: ticket history (incident/change/tuning), the change calendar,
and patch inventory — the "key evidence" for Patch Management and the ticket-history evidence
source for Incident Resolution (domain-workflows.md parity table). Fully synthetic, fixed seed.

    python data_gen/tickets.py

Writes:
    data/tickets.csv           400-600 rows: sys_id,type,status,ci_id,opened_at,closed_at,priority,short_description
    data/change_calendar.json  scheduled maintenance windows
    data/patch_inventory.csv   per-CI patch/version gap
"""
import csv
import json
import os
import random
from datetime import timedelta

from faker import Faker

SEED = 20260807
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

TICKET_COUNT = 500
CHANGE_WINDOW_COUNT = 25

TICKET_TYPES = ["incident", "change", "tuning_task"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
INCIDENT_DESCRIPTIONS = [
    "Service outage - {ci}", "Elevated error rate on {ci}", "{ci} health check failing",
    "Disk space critical on {ci}", "Connection timeouts to {ci}",
]
CHANGE_DESCRIPTIONS = ["Scheduled patch window for {ci}", "Config rollout for {ci}", "Cert rotation for {ci}"]
TUNING_DESCRIPTIONS = ["Latency tuning investigation for {ci}", "Memory usage tuning for {ci}", "Query optimisation review for {ci}"]
CHANGE_TYPES = ["patch", "config", "tuning"]


def _load_cis() -> list[dict]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return json.load(f)["cis"]


def generate_tickets(cis: list[dict]) -> list[dict]:
    tickets = []
    for i in range(1, TICKET_COUNT + 1):
        ci = random.choice(cis)
        ttype = random.choice(TICKET_TYPES)
        desc_pool = {"incident": INCIDENT_DESCRIPTIONS, "change": CHANGE_DESCRIPTIONS, "tuning_task": TUNING_DESCRIPTIONS}[ttype]
        opened = fake.date_time_between(start_date="-180d", end_date="-1d")
        is_closed = random.random() < 0.85
        closed = opened + timedelta(hours=random.uniform(0.5, 96)) if is_closed else None
        tickets.append({
            "sys_id": f"TCK-{i:04d}",
            "type": ttype,
            "status": "closed" if is_closed else random.choice(["open", "in_progress"]),
            "ci_id": ci["id"],
            "opened_at": opened.isoformat(),
            "closed_at": closed.isoformat() if closed else "",
            "priority": random.choice(PRIORITIES),
            "short_description": random.choice(desc_pool).format(ci=ci["name"]),
        })
    return tickets


def generate_change_calendar(cis: list[dict]) -> list[dict]:
    windows = []
    for i in range(1, CHANGE_WINDOW_COUNT + 1):
        ci = random.choice(cis)
        start = fake.date_time_between(start_date="now", end_date="+30d")
        windows.append({
            "id": f"CHG-{i:03d}",
            "ci_id": ci["id"],
            "window_start": start.isoformat(),
            "window_end": (start + timedelta(hours=random.uniform(1, 4))).isoformat(),
            "change_type": random.choice(CHANGE_TYPES),
            "description": f"Maintenance window for {ci['name']}",
        })
    return windows


def generate_patch_inventory(cis: list[dict]) -> list[dict]:
    rows = []
    for ci in cis:
        current = ci["patch_level"]
        major, minor, patch = (int(x) for x in current.split("."))
        available = f"{major}.{minor}.{patch + random.randint(1, 4)}"
        rows.append({
            "ci_id": ci["id"],
            "patch_name": f"{ci['type']}-security-update",
            "current_version": current,
            "available_version": available,
            "cve_ref": f"CVE-2026-{random.randint(10000, 99999)}",
            "severity": random.choice(["critical", "high", "medium", "low"]),
            "released_at": fake.date_time_between(start_date="-30d", end_date="-1d").isoformat(),
        })
    return rows


def main() -> None:
    cis = _load_cis()
    os.makedirs(DATA_DIR, exist_ok=True)

    tickets = generate_tickets(cis)
    with open(os.path.join(DATA_DIR, "tickets.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tickets[0].keys()))
        writer.writeheader()
        writer.writerows(tickets)

    change_calendar = generate_change_calendar(cis)
    with open(os.path.join(DATA_DIR, "change_calendar.json"), "w", encoding="utf-8") as f:
        json.dump(change_calendar, f, indent=2)

    patch_inventory = generate_patch_inventory(cis)
    with open(os.path.join(DATA_DIR, "patch_inventory.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(patch_inventory[0].keys()))
        writer.writeheader()
        writer.writerows(patch_inventory)

    print(f"tickets.csv: {len(tickets)} rows")
    print(f"change_calendar.json: {len(change_calendar)} windows")
    print(f"patch_inventory.csv: {len(patch_inventory)} rows")


if __name__ == "__main__":
    main()

    with open(os.path.join(DATA_DIR, "tickets.csv"), encoding="utf-8") as f:
        tickets = list(csv.DictReader(f))
    assert 400 <= len(tickets) <= 600, f"ticket count {len(tickets)} outside 400-600 band"
    assert {t["type"] for t in tickets} == set(TICKET_TYPES), "not all 3 ticket types present"

    with open(os.path.join(DATA_DIR, "change_calendar.json"), encoding="utf-8") as f:
        calendar = json.load(f)
    assert len(calendar) == CHANGE_WINDOW_COUNT

    with open(os.path.join(DATA_DIR, "patch_inventory.csv"), encoding="utf-8") as f:
        patches = list(csv.DictReader(f))
    ci_ids = {ci["id"] for ci in _load_cis()}
    assert len(patches) == len(ci_ids), "patch inventory should cover every CI"
    assert all(p["ci_id"] in ci_ids for p in patches)

    print("\nSELF-TEST PASSED: ticket volume/type coverage, change calendar, and patch inventory all valid.")
