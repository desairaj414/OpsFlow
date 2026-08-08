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

# Plain-language product label per CI type — a first-time user reads "SharePoint Site", not
# "sharepoint-site" or a bare CI-0084 id (Ops Board readability pass).
CI_TYPE_LABEL = {
    "sharepoint-site": "SharePoint Site",
    "power-platform-environment": "Power Platform Environment",
    "dataverse-instance": "Dataverse Environment",
    "exchange-online-connector": "Exchange Online Connector",
    "power-automate-gateway": "Power Automate Gateway",
    "onedrive-sync-cache": "OneDrive Sync Cache",
    "teams-notification-queue": "Teams Notification Queue",
    "sharepoint-document-library": "SharePoint Document Library",
    "azure-ad-connect-sync": "Azure AD Connect Sync",
}
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
        name = f"{ci_type}-{fake.word()}-{i:03d}"
        cis.append({
            "id": _ci_id(i),
            "name": name,
            "display_name": f"{CI_TYPE_LABEL[ci_type]} ({name})",
            "type": ci_type,
            "owner": random.choice(OWNER_TEAMS),
            "environment": random.choice(ENVIRONMENTS),
            "criticality": random.choice(CRITICALITIES),
            "patch_level": f"{random.randint(1, 9)}.{random.randint(0, 20)}.{random.randint(0, 9)}",
            "last_verified_at": fake.date_time_between(start_date="-90d", end_date="-1d").isoformat(),
        })
    return cis


# Test/scenario fixtures pin specific blast-radius shapes on these CIs (test_supervisor.py,
# test_planner.py, data/scenarios/SCEN-0{1,2,3}.json) — guaranteed regardless of the random
# neighborhood assignment below, the same pattern data_gen/patch_inventory.py uses for its own
# guaranteed-coverage CIs.
ISOLATED_CI_IDS = ["CI-0059", "CI-0121"]  # must stay low blast-radius (SCEN-01/02: "clean"/"fake fix" happy paths)
HUB_CI_ID = "CI-0009"  # must stay > the policy gate's block threshold (SCEN-03: high-blast-radius block)
HUB_SPOKE_COUNT = 20


def generate_relationships(cis: list[dict]) -> list[dict]:
    """Adjacency table per schema-db.md: cmdb_relationship(ci_id, related_ci_id, relation_type).
    Relationships are deliberately LOCALIZED — small neighborhoods (2-6 CIs), grouped by
    (environment, owner) so a neighborhood models one team's one environment, the way a real
    dependency chain actually sits (an app depending on a DB depending on a host, all the same
    team's prod stack) — not random edges across the whole 200-CI dataset.

    A prior version connected every CI to a uniformly random other CI. At this CI count/edge
    density that's a classic random-graph setup that (per Erdos-Renyi giant-component math)
    collapses into ONE ~190-CI connected component almost every time — confirmed empirically
    (190/200 CIs in one topology group). That made correlation/cluster.py's topology-based
    grouping nearly meaningless: two alerts on completely unrelated CIs (e.g. different SharePoint
    sites with no real dependency) would still land in the same candidate cluster/incident/ticket
    just because they were both in that one blob, not because of any real shared root cause. See
    state-progress.md's "success metrics / ID scheme" write-up for the user-facing symptom."""
    relationships = []
    by_group: dict[tuple[str, str], list[dict]] = {}
    for ci in cis:
        if ci["id"] in ISOLATED_CI_IDS or ci["id"] == HUB_CI_ID:
            continue  # handled explicitly below, never folded into a random neighborhood
        by_group.setdefault((ci["environment"], ci["owner"]), []).append(ci)

    for group_cis in by_group.values():
        pool = group_cis[:]
        random.shuffle(pool)
        while pool:
            size = min(len(pool), random.randint(2, 6))
            if size < 2:
                pool.pop()  # a lone leftover CI in this group — no relationship, realistic too
                continue
            neighborhood = [pool.pop() for _ in range(size)]
            # Random spanning tree over the neighborhood: guarantees it's one connected component,
            # bounded to `size` CIs, never bleeding into another neighborhood.
            shuffled = neighborhood[:]
            random.shuffle(shuffled)
            for i in range(1, len(shuffled)):
                parent = shuffled[random.randint(0, i - 1)]
                relationships.append({
                    "ci_id": shuffled[i]["id"], "related_ci_id": parent["id"],
                    "relation_type": random.choice(RELATION_TYPES),
                })
            # A little extra texture (a neighborhood isn't always a strict tree) without risking
            # a bridge back out to another neighborhood.
            for _ in range(random.randint(0, size // 3)):
                a, b = random.sample(neighborhood, 2)
                relationships.append({"ci_id": a["id"], "related_ci_id": b["id"], "relation_type": random.choice(RELATION_TYPES)})

    # HUB_CI_ID: a deliberate high-fan-out CI — realistic in its own right (shared identity/auth
    # infra, a central Dataverse instance, etc. genuinely does have dozens of dependents in a real
    # CMDB) and required so at least one scenario can demonstrate the policy gate's hard block.
    other_ids = [ci["id"] for ci in cis if ci["id"] != HUB_CI_ID and ci["id"] not in ISOLATED_CI_IDS]
    for spoke in random.sample(other_ids, min(HUB_SPOKE_COUNT, len(other_ids))):
        relationships.append({"ci_id": HUB_CI_ID, "related_ci_id": spoke, "relation_type": random.choice(RELATION_TYPES)})

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
    required_fields = {"id", "name", "display_name", "type", "owner", "environment", "criticality", "patch_level", "last_verified_at"}
    assert required_fields.issubset(cmdb["cis"][0].keys()), "CI missing a required schema-db.md field"
    diverged_count = sum(1 for ci in gt if "_diverged_field" in ci)
    diverged_rate = diverged_count / CI_COUNT
    assert 0.25 <= diverged_rate <= 0.45, f"divergence rate {diverged_rate:.0%} outside expected ~35% band"
    assert len(failed) == FAILED_REMEDIATION_COUNT

    # --- relationship-topology self-check: localized neighborhoods, not one giant blob ---
    def _build_adjacency(rels: list[dict]) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = {}
        for r in rels:
            adj.setdefault(r["ci_id"], set()).add(r["related_ci_id"])
            adj.setdefault(r["related_ci_id"], set()).add(r["ci_id"])
        return adj

    def _blast_radius(ci_id: str, adj: dict[str, set[str]], max_depth: int = 2) -> int:
        visited = {ci_id}
        frontier = [(ci_id, 0)]
        while frontier:
            node, depth = frontier.pop()
            if depth >= max_depth:
                continue
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    frontier.append((neighbor, depth + 1))
        return len(visited) - 1

    adjacency = _build_adjacency(cmdb["relationships"])
    # Connected-component sizes with HUB_CI_ID's edges removed entirely (not just skipped as a
    # start node) — its high fan-out is deliberate (SCEN-03 needs a real, large blast radius to
    # demonstrate the policy gate's block), so it's expected to bridge many spokes together; that's
    # not the bug this checks for. What this DOES catch: any *other*, non-hub neighborhood
    # sprawling large — the original giant-component bug.
    non_hub_adjacency = {
        ci_id: {n for n in neighbors if n != HUB_CI_ID}
        for ci_id, neighbors in adjacency.items() if ci_id != HUB_CI_ID
    }
    seen: set[str] = set()
    component_sizes = []
    for ci_id in non_hub_adjacency:
        if ci_id in seen:
            continue
        stack, component = [ci_id], set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(non_hub_adjacency.get(node, set()) - component)
        seen |= component
        component_sizes.append(len(component))
    max_non_hub_component = max(component_sizes) if component_sizes else 0
    assert max_non_hub_component <= 10, f"a non-hub topology neighborhood has {max_non_hub_component} CIs — relationships are collapsing into one blob again"
    print(f"Relationship topology: {len(component_sizes)} non-hub connected components, largest has {max_non_hub_component} CIs (was 190/200 before the localized-neighborhood fix)")

    hub_br = _blast_radius(HUB_CI_ID, adjacency)
    assert hub_br > 15, f"{HUB_CI_ID} blast radius is {hub_br}, must stay > 15 (policy gate block threshold) for SCEN-03/test_supervisor.py"
    for isolated_id in ISOLATED_CI_IDS:
        br = _blast_radius(isolated_id, adjacency)
        assert br <= 5, f"{isolated_id} blast radius is {br}, must stay low for SCEN-01/02/test_supervisor.py's happy-path scenarios"
    print(f"Guaranteed blast-radius shapes intact: {HUB_CI_ID}={hub_br} (>15), " + ", ".join(f"{i}={_blast_radius(i, adjacency)}" for i in ISOLATED_CI_IDS) + " (<=5)")

    print("\nSELF-TEST PASSED: shapes, volumes, divergence rate, and relationship topology all within expected bounds.")
