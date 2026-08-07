"""Deterministic alert correlation — NO LLM (arch-overview.md routing principle: correlation is a
deterministic task, an LLM here would be non-deterministic, expensive, and worse than clustering
at it — see decisions-log.md). Combines 3 signals:
  - fingerprint: (topology_group, category) — a coarse bucket key
  - topology: CI relationship graph connected components (from cmdb.json), so an alert on a DB and
    a dependent app-server land in the same topology group
  - time-window: scikit-learn DBSCAN over each bucket's timestamps, so only alerts close in time
    within the same topology/category bucket become one candidate cluster

    python correlation/cluster.py         # run against data/alerts.json + data/cmdb.json
    python correlation/cluster.py --test  # + reproducibility and correctness self-checks
"""
import json
import os
import sys
from datetime import datetime

import numpy as np
from sklearn.cluster import DBSCAN

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

TIME_WINDOW_SECONDS = 900  # 15 min — alerts further apart than this never share a cluster


def _load_cis_and_relationships() -> tuple[list[dict], list[dict]]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data["cis"], data["relationships"]


def _load_alerts() -> list[dict]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        return json.load(f)


def build_topology_groups(cis: list[dict], relationships: list[dict]) -> dict[str, int]:
    """Connected components over the CI relationship graph (undirected for grouping purposes) —
    a deterministic union-find, not a black-box graph library, so behaviour is auditable."""
    parent = {ci["id"]: ci["id"] for ci in cis}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for rel in relationships:
        if rel["ci_id"] in parent and rel["related_ci_id"] in parent:
            union(rel["ci_id"], rel["related_ci_id"])

    # Stable numeric group ids: sorted by the group's smallest CI id, so output is reproducible
    # across runs regardless of dict/set iteration order.
    roots = sorted({find(ci_id) for ci_id in parent})
    root_to_group = {root: i for i, root in enumerate(roots)}
    return {ci_id: root_to_group[find(ci_id)] for ci_id in parent}


def _epoch_seconds(iso_ts: str) -> float:
    return datetime.fromisoformat(iso_ts).timestamp()


def correlate_alerts(alerts: list[dict], topology_groups: dict[str, int]) -> list[dict]:
    """Returns each alert tagged with a cluster_id. Alerts sharing (topology_group, category) are
    bucketed, then DBSCAN groups them further by time proximity within the bucket."""
    # Sort first so cluster_id assignment order is deterministic regardless of input ordering.
    ordered = sorted(alerts, key=lambda a: (a["ci_id"], a["category"], a["received_at"], a["id"]))

    buckets: dict[tuple[int, str], list[dict]] = {}
    for alert in ordered:
        group = topology_groups.get(alert["ci_id"], -1)
        key = (group, alert["category"])
        buckets.setdefault(key, []).append(alert)

    cluster_id = 0
    results = []
    for key in sorted(buckets.keys()):
        bucket_alerts = buckets[key]
        timestamps = np.array([[_epoch_seconds(a["received_at"])] for a in bucket_alerts])
        labels = DBSCAN(eps=TIME_WINDOW_SECONDS, min_samples=1).fit_predict(timestamps)
        # Remap DBSCAN's local labels to globally unique, order-stable cluster ids.
        local_to_global = {}
        for local_label in sorted(set(labels)):
            local_to_global[local_label] = cluster_id
            cluster_id += 1
        for alert, local_label in zip(bucket_alerts, labels):
            results.append({**alert, "cluster_id": local_to_global[local_label], "topology_group": key[0]})

    return sorted(results, key=lambda a: a["id"])


def main() -> None:
    cis, relationships = _load_cis_and_relationships()
    alerts = _load_alerts()
    topology_groups = build_topology_groups(cis, relationships)
    correlated = correlate_alerts(alerts, topology_groups)
    n_clusters = len({a["cluster_id"] for a in correlated})
    print(f"{len(alerts)} alerts -> {n_clusters} candidate clusters across {len(set(topology_groups.values()))} topology groups")
    return correlated


if __name__ == "__main__":
    result = main()

    if "--test" in sys.argv:
        cis, relationships = _load_cis_and_relationships()
        alerts = _load_alerts()
        topology_groups = build_topology_groups(cis, relationships)

        # Reproducibility: same input -> same output (Phase 2 acceptance criterion #1).
        run1 = correlate_alerts(alerts, topology_groups)
        run2 = correlate_alerts(alerts, topology_groups)
        assert run1 == run2, "correlation is not reproducible — same input produced different output"
        print("PASS: correlation is reproducible (same input -> identical output across runs)")

        # Alerts on the same CI, same category, close in time must land in the same cluster.
        by_ci_category: dict[tuple[str, str], list[dict]] = {}
        for a in run1:
            by_ci_category.setdefault((a["ci_id"], a["category"]), []).append(a)
        found_case = False
        for (ci_id, category), group in by_ci_category.items():
            if len(group) < 2:
                continue
            group_sorted = sorted(group, key=lambda a: a["received_at"])
            for a, b in zip(group_sorted, group_sorted[1:]):
                gap = abs(_epoch_seconds(b["received_at"]) - _epoch_seconds(a["received_at"]))
                if gap <= TIME_WINDOW_SECONDS:
                    found_case = True
                    assert a["cluster_id"] == b["cluster_id"], f"alerts {a['id']}/{b['id']} on same CI within {gap:.0f}s were NOT clustered together"
        assert found_case, "no same-CI/same-category/close-in-time pair found in the dataset to test against"
        print("PASS: same-CI, same-category, close-in-time alerts correctly land in the same cluster")

        # A single alert's cluster must never span two different CIs from different topology groups.
        for a in run1:
            assert a["topology_group"] == topology_groups[a["ci_id"]]
        print("PASS: topology grouping matches the CI relationship graph")

        print(f"\nSELF-TEST PASSED: correlation engine deterministic and structurally correct ({len(run1)} alerts processed).")
