"""Blast-radius computation from the CMDB adjacency table (schema-db.md `cmdb_relationship`).
Pure graph BFS, no LLM — this number feeds the policy gate's BLAST_RADIUS thresholds directly, so
it must be deterministic and auditable. Relationships are treated as undirected for this purpose:
any recorded coupling (depends_on/hosts/connects_to/replicates_to) means an action on one CI can
plausibly ripple to the other, regardless of edge direction.
"""
from collections import deque

DEFAULT_MAX_DEPTH = 2


def build_adjacency(relationships: list[dict]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for rel in relationships:
        a, b = rel["ci_id"], rel["related_ci_id"]
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    return adjacency


def compute_blast_radius(ci_id: str, relationships: list[dict], max_depth: int = DEFAULT_MAX_DEPTH) -> dict:
    """BFS out to max_depth hops. Returns the affected CI ids (never including ci_id itself) and count."""
    adjacency = build_adjacency(relationships)
    visited = {ci_id}
    frontier = deque([(ci_id, 0)])
    affected: list[str] = []

    while frontier:
        node, depth = frontier.popleft()
        if depth >= max_depth:
            continue
        for neighbor in sorted(adjacency.get(node, set())):
            if neighbor not in visited:
                visited.add(neighbor)
                affected.append(neighbor)
                frontier.append((neighbor, depth + 1))

    return {"ci_id": ci_id, "affected_ci_ids": affected, "count": len(affected), "max_depth": max_depth}
