"""Generates the synthetic CMDB: as-recorded CIs, a diverged ground-truth copy, and
failed-remediation seeds for the Negative KB. All fully synthetic — no real/customer data
(PRD §6.3). Fixed seed so the dataset is reproducible across runs (same file every time).

    python data_gen/cmdb.py

Writes (repo root):
    data/cmdb.json                 ~200 CIs, as recorded
    data/cmdb_ground_truth.json    same CIs, ~35% deliberately diverged from as-recorded
    data/failed_remediations.json  ~40 seeds for negative_kb_entries (schema-db.md)
"""
import json
import os
import random

from faker import Faker

SEED = 20260807
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

CI_COUNT = 200
GROUND_TRUTH_DIVERGENCE_RATE = 0.35
FAILED_REMEDIATION_COUNT = 40

CI_TYPES = ["sharepoint-site", "power-platform-environment", "dataverse-instance", "exchange-online-connector", "power-automate-gateway", "onedrive-sync-cache", "teams-notification-queue", "sharepoint-document-library", "azure-ad-connect-sync"]
ENVIRONMENTS = ["prod", "staging", "dev"]
CRITICALITIES = ["P1", "P2", "P3", "P4"]
OWNER_TEAMS = ["Sales", "Marketing", "Finance", "HR", "Legal", "Engineering", "Customer Success", "Global IT"]
RELATION_TYPES = ["depends_on", "hosts", "connects_to", "replicates_to"]

FAILURE_SIGNATURES = [
    "access denied on SharePoint site collection", "OneDrive sync stuck / not syncing",
    "Power Automate flow run failures (throttled)", "Dataverse API throttling (429)",
    "Conditional Access policy blocking sign-in", "SharePoint document library storage quota exceeded",
    "Exchange Online mail delivery delayed", "Power BI dataset refresh failure",
    "Teams meeting audio/video degraded", "Azure AD Connect sync interruption",
]
ATTEMPTED_FIXES = [
    "re-granted site permissions", "restarted the OneDrive sync client", "increased the connector throttling limit",
    "requested a Dataverse capacity add-on", "added the user to the Conditional Access exclusion group",
    "requested additional SharePoint storage quota", "restarted the Exchange Online transport queue", "cleared the Teams client cache",
]
FAILURE_REASONS = [
    "root cause was a broken permission-inheritance chain, not a simple access grant",
    "fix addressed a symptom, underlying license assignment was still missing",
    "the Conditional Access policy was reapplied by the next sync cycle",
    "the throttling limit increase did not address the actual API call volume spike",
    "the exclusion group itself was scoped incorrectly",
]


def _ci_id(i: int) -> str:
    return f"CI-{i:04d}"


def generate_cis() -> list[dict]:
    cis = []
    for i in range(1, CI_COUNT + 1):
        ci_type = random.choice(CI_TYPES)
        cis.append({
            "id": _ci_id(i),
            "name": f"{ci_type}-{fake.word()}-{i:03d}",
            "type": ci_type,
            "owner": random.choice(OWNER_TEAMS),
            "environment": random.choice(ENVIRONMENTS),
            "criticality": random.choice(CRITICALITIES),
            "patch_level": f"{random.randint(1, 9)}.{random.randint(0, 20)}.{random.randint(0, 9)}",
            "last_verified_at": fake.date_time_between(start_date="-90d", end_date="-1d").isoformat(),
        })
    return cis


def generate_relationships(cis: list[dict]) -> list[dict]:
    """Adjacency table per schema-db.md: cmdb_relationship(ci_id, related_ci_id, relation_type).
    Each CI gets 0-3 outgoing relationships to a different, randomly chosen CI."""
    relationships = []
    ids = [ci["id"] for ci in cis]
    for ci in cis:
        for _ in range(random.randint(0, 3)):
            related = random.choice(ids)
            if related == ci["id"]:
                continue
            relationships.append({
                "ci_id": ci["id"],
                "related_ci_id": related,
                "relation_type": random.choice(RELATION_TYPES),
            })
    return relationships


def diverge_ground_truth(cis: list[dict]) -> list[dict]:
    """~35% of CIs get one field deliberately wrong vs. as-recorded — this IS the CMDB drift
    the Drift-vs-Truth screen demonstrates (real CMDBs are notoriously inaccurate; see citations.md)."""
    ground_truth = [dict(ci) for ci in cis]
    diverge_count = round(len(ground_truth) * GROUND_TRUTH_DIVERGENCE_RATE)
    diverge_indices = random.sample(range(len(ground_truth)), diverge_count)
    for idx in diverge_indices:
        ci = ground_truth[idx]
        field = random.choice(["patch_level", "criticality", "environment", "owner"])
        if field == "patch_level":
            ci["patch_level"] = f"{random.randint(1, 9)}.{random.randint(0, 20)}.{random.randint(0, 9)}"
        elif field == "criticality":
            ci["criticality"] = random.choice([c for c in CRITICALITIES if c != ci["criticality"]])
        elif field == "environment":
            ci["environment"] = random.choice([e for e in ENVIRONMENTS if e != ci["environment"]])
        elif field == "owner":
            ci["owner"] = random.choice([o for o in OWNER_TEAMS if o != ci["owner"]])
        ci["_diverged_field"] = field  # dev-only marker; strip before any UI/demo exposure
    return ground_truth


def generate_failed_remediations(cis: list[dict]) -> list[dict]:
    """Seeds negative_kb_entries (schema-db.md) — remediations tried and known NOT to work,
    so agents can avoid repeating them, not just find known-good fixes."""
    entries = []
    for i in range(1, FAILED_REMEDIATION_COUNT + 1):
        ci = random.choice(cis)
        entries.append({
            "id": f"NEGKB-{i:03d}",
            "ci_class": ci["type"],
            "failure_signature": random.choice(FAILURE_SIGNATURES),
            "attempted_fix": random.choice(ATTEMPTED_FIXES),
            "reason_failed": random.choice(FAILURE_REASONS),
            "source_incident_id": f"INC-{random.randint(1000, 9999)}",
        })
    return entries


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    cis = generate_cis()
    relationships = generate_relationships(cis)
    ground_truth = diverge_ground_truth(cis)
    failed_remediations = generate_failed_remediations(cis)

    with open(os.path.join(DATA_DIR, "cmdb.json"), "w", encoding="utf-8") as f:
        json.dump({"cis": cis, "relationships": relationships}, f, indent=2)
    with open(os.path.join(DATA_DIR, "cmdb_ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    with open(os.path.join(DATA_DIR, "failed_remediations.json"), "w", encoding="utf-8") as f:
        json.dump(failed_remediations, f, indent=2)

    print(f"cmdb.json: {len(cis)} CIs, {len(relationships)} relationships")
    diverged = sum(1 for gt in ground_truth if "_diverged_field" in gt)
    print(f"cmdb_ground_truth.json: {len(ground_truth)} CIs, {diverged} diverged ({diverged/len(ground_truth):.0%})")
    print(f"failed_remediations.json: {len(failed_remediations)} entries")


if __name__ == "__main__":
    main()

    # --- self-test: shape + volume + divergence-rate sanity checks ---
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        cmdb = json.load(f)
    with open(os.path.join(DATA_DIR, "cmdb_ground_truth.json"), encoding="utf-8") as f:
        gt = json.load(f)
    with open(os.path.join(DATA_DIR, "failed_remediations.json"), encoding="utf-8") as f:
        failed = json.load(f)

    assert len(cmdb["cis"]) == CI_COUNT, f"expected {CI_COUNT} CIs, got {len(cmdb['cis'])}"
    assert len(gt) == CI_COUNT
    required_fields = {"id", "name", "type", "owner", "environment", "criticality", "patch_level", "last_verified_at"}
    assert required_fields.issubset(cmdb["cis"][0].keys()), "CI missing a required schema-db.md field"
    diverged_count = sum(1 for ci in gt if "_diverged_field" in ci)
    diverged_rate = diverged_count / CI_COUNT
    assert 0.25 <= diverged_rate <= 0.45, f"divergence rate {diverged_rate:.0%} outside expected ~35% band"
    assert len(failed) == FAILED_REMEDIATION_COUNT
    print("\nSELF-TEST PASSED: shapes, volumes, and divergence rate all within expected bounds.")
