"""Generates the synthetic Patch Inventory (pending vendor patches per CI) and Change Calendar
(blackout/freeze windows) — the two data sources PRD row 816 and clause C6 call for but Phase 1
never built: "Patch inventory | CSV | Pending patches per CI, severity, dependencies" and
"intelligent scheduling — dependency-aware, blackout-aware, SLA-aware". All fully synthetic — no
real/customer data (PRD §6.3). Fixed seed so the dataset is reproducible across runs.

    python data_gen/patch_inventory.py

Writes (repo root):
    data/patch_inventory.json   pending patches per CI (~40% of CIs have 1-3 each)
    data/change_calendar.json   blackout/freeze windows (global, per-environment, per-CI)
"""
import json
import os
import random
from datetime import datetime, timedelta, timezone

from faker import Faker

SEED = 20260807
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

# CI-0059 is the fixed CI the patch scenario (data/scenarios/SCEN-04.json) and the Supervisor
# patch-workflow test (tests/test_supervisor.py) both run against — guarantee it has real,
# dependency-linked pending patches so the scheduling feature is actually exercised, not just
# reachable by chance from the random 40% coverage below.
GUARANTEED_PATCH_CI_IDS = ["CI-0059", "CI-0121"]

PATCH_COVERAGE_RATE = 0.40
VENDORS = ["Microsoft", "Adobe", "Cisco", "Oracle", "Red Hat", "VMware"]
SEVERITIES = ["critical", "high", "medium", "low"]
# Vendor SLA convention this dataset follows (matches common patch-management practice — cited in
# citations.md): critical patches must land fast, low severity can wait.
SLA_DAYS_BY_SEVERITY = {"critical": 7, "high": 14, "medium": 30, "low": 60}

BLACKOUT_REASONS = [
    "Quarter-end financial close freeze", "Regional public holiday freeze", "Peak sales-season freeze",
    "Annual audit freeze", "Data-center maintenance window (vendor-mandated)", "Year-end code freeze",
]


def _load_cis() -> list[dict]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return json.load(f)["cis"]


def generate_patch_inventory(cis: list[dict]) -> list[dict]:
    """Pending patches per CI. A CI's 2nd+ patch may depend_on an earlier patch for the SAME ci_id
    (dependency-aware scheduling has to sequence those correctly, not just group by severity)."""
    by_id = {ci["id"]: ci for ci in cis}
    eligible_ids = {ci["id"] for ci in cis if random.random() < PATCH_COVERAGE_RATE}
    eligible_ids.update(GUARANTEED_PATCH_CI_IDS)

    patches: list[dict] = []
    counter = 1
    now = datetime.now(timezone.utc)
    for ci_id in sorted(eligible_ids):
        if ci_id not in by_id:
            continue  # a guaranteed id that isn't in this CMDB generation run — skip, don't fabricate
        n = random.randint(1, 3)
        prior_id_for_ci: str | None = None
        for _ in range(n):
            severity = random.choice(SEVERITIES)
            patch_id = f"PATCH-{counter:04d}"
            counter += 1
            released_at = now - timedelta(days=random.randint(1, 45))
            depends_on = [prior_id_for_ci] if prior_id_for_ci and random.random() < 0.5 else []
            patches.append({
                "id": patch_id,
                "ci_id": ci_id,
                "vendor": random.choice(VENDORS),
                "title": f"{random.choice(VENDORS)} security update for {by_id[ci_id]['type']}",
                "severity": severity,
                "cve_ids": [f"CVE-2026-{random.randint(10000, 99999)}"] if severity in ("critical", "high") else [],
                "released_at": released_at.isoformat(),
                "sla_days": SLA_DAYS_BY_SEVERITY[severity],
                "depends_on_patch_ids": depends_on,
                "status": "pending",
            })
            prior_id_for_ci = patch_id
    return patches


def generate_change_calendar(cis: list[dict]) -> list[dict]:
    """Blackout/freeze windows: a mix of global, per-environment, and per-CI scopes so the
    scheduling engine has to check all three, not just one lookup key."""
    now = datetime.now(timezone.utc)
    windows = []
    # Global freezes (apply to every CI regardless of environment).
    for i in range(3):
        start = now + timedelta(days=random.randint(2, 50))
        windows.append({
            "id": f"BLACKOUT-G{i+1:02d}", "scope": "global",
            "starts_at": start.isoformat(), "ends_at": (start + timedelta(days=random.randint(1, 4))).isoformat(),
            "reason": random.choice(BLACKOUT_REASONS),
        })
    # Per-environment freezes.
    for i, env in enumerate(["prod", "staging", "dev"]):
        start = now + timedelta(days=random.randint(1, 40))
        windows.append({
            "id": f"BLACKOUT-E{i+1:02d}", "scope": env,
            "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=random.randint(6, 48))).isoformat(),
            "reason": random.choice(BLACKOUT_REASONS),
        })
    # A few per-CI freezes, including one on CI-0059 so the guaranteed patch scenario has a real
    # blackout to route around, not just environment-level ones.
    per_ci_targets = GUARANTEED_PATCH_CI_IDS + [random.choice(cis)["id"] for _ in range(4)]
    for i, ci_id in enumerate(per_ci_targets):
        start = now + timedelta(days=random.randint(1, 10))
        windows.append({
            "id": f"BLACKOUT-C{i+1:02d}", "scope": ci_id,
            "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=random.randint(4, 24))).isoformat(),
            "reason": "Owner-requested change freeze",
        })
    return windows


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    cis = _load_cis()
    patches = generate_patch_inventory(cis)
    calendar = generate_change_calendar(cis)

    with open(os.path.join(DATA_DIR, "patch_inventory.json"), "w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2)
    with open(os.path.join(DATA_DIR, "change_calendar.json"), "w", encoding="utf-8") as f:
        json.dump(calendar, f, indent=2)

    covered_cis = {p["ci_id"] for p in patches}
    print(f"patch_inventory.json: {len(patches)} patches across {len(covered_cis)} CIs")
    print(f"change_calendar.json: {len(calendar)} blackout windows")


if __name__ == "__main__":
    main()

    # --- self-test: shape + guaranteed-coverage + dependency-integrity checks ---
    with open(os.path.join(DATA_DIR, "patch_inventory.json"), encoding="utf-8") as f:
        patches = json.load(f)
    with open(os.path.join(DATA_DIR, "change_calendar.json"), encoding="utf-8") as f:
        calendar = json.load(f)

    required_patch_fields = {"id", "ci_id", "vendor", "title", "severity", "cve_ids", "released_at", "sla_days", "depends_on_patch_ids", "status"}
    assert required_patch_fields.issubset(patches[0].keys())
    ids = {p["id"] for p in patches}
    for p in patches:
        for dep in p["depends_on_patch_ids"]:
            assert dep in ids, f"{p['id']} depends on unknown patch {dep}"
            dep_ci = next(x for x in patches if x["id"] == dep)["ci_id"]
            assert dep_ci == p["ci_id"], f"{p['id']} depends on a patch for a different CI"

    covered = {p["ci_id"] for p in patches}
    for guaranteed in GUARANTEED_PATCH_CI_IDS:
        assert guaranteed in covered, f"{guaranteed} must have guaranteed pending patches"

    required_cal_fields = {"id", "scope", "starts_at", "ends_at", "reason"}
    assert required_cal_fields.issubset(calendar[0].keys())
    scopes = {w["scope"] for w in calendar}
    assert "global" in scopes and "prod" in scopes and "CI-0059" in scopes
    print(f"\nSELF-TEST PASSED: {len(patches)} patches ({len(covered)} CIs covered, guaranteed CIs present, "
          f"dependency chains internally consistent), {len(calendar)} blackout windows (global/env/CI scopes all present).")
