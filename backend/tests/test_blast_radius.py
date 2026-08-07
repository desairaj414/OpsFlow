"""Unit tests for blast-radius computation against known, hand-built CMDB adjacency fixtures
(not the randomized generated data — a fixed graph with a hand-verifiable expected answer)."""
from guardrails.blast_radius import compute_blast_radius

# Fixture graph: A -- B -- C -- D  (a simple chain), plus E isolated, plus F -- G -- H (separate chain)
CHAIN_FIXTURE = [
    {"ci_id": "A", "related_ci_id": "B", "relation_type": "depends_on"},
    {"ci_id": "B", "related_ci_id": "C", "relation_type": "connects_to"},
    {"ci_id": "C", "related_ci_id": "D", "relation_type": "hosts"},
    {"ci_id": "F", "related_ci_id": "G", "relation_type": "depends_on"},
    {"ci_id": "G", "related_ci_id": "H", "relation_type": "depends_on"},
]

# Fixture graph: star topology, X connected directly to 5 leaves.
STAR_FIXTURE = [{"ci_id": "X", "related_ci_id": leaf, "relation_type": "hosts"} for leaf in ["L1", "L2", "L3", "L4", "L5"]]


def test_chain_depth_1_reaches_only_direct_neighbors():
    result = compute_blast_radius("B", CHAIN_FIXTURE, max_depth=1)
    assert set(result["affected_ci_ids"]) == {"A", "C"}
    assert result["count"] == 2


def test_chain_depth_2_reaches_two_hops():
    result = compute_blast_radius("A", CHAIN_FIXTURE, max_depth=2)
    assert set(result["affected_ci_ids"]) == {"B", "C"}
    assert result["count"] == 2


def test_chain_depth_3_reaches_full_chain():
    result = compute_blast_radius("A", CHAIN_FIXTURE, max_depth=3)
    assert set(result["affected_ci_ids"]) == {"B", "C", "D"}
    assert result["count"] == 3


def test_isolated_ci_has_zero_blast_radius():
    result = compute_blast_radius("E", CHAIN_FIXTURE, max_depth=2)
    assert result["affected_ci_ids"] == []
    assert result["count"] == 0


def test_unrelated_subgraph_not_reached():
    result = compute_blast_radius("A", CHAIN_FIXTURE, max_depth=10)
    assert "F" not in result["affected_ci_ids"]
    assert "G" not in result["affected_ci_ids"]
    assert "H" not in result["affected_ci_ids"]


def test_star_topology_hub_reaches_all_leaves_at_depth_1():
    result = compute_blast_radius("X", STAR_FIXTURE, max_depth=1)
    assert set(result["affected_ci_ids"]) == {"L1", "L2", "L3", "L4", "L5"}
    assert result["count"] == 5


def test_star_topology_leaf_reaches_hub_and_siblings_at_depth_2():
    result = compute_blast_radius("L1", STAR_FIXTURE, max_depth=2)
    assert set(result["affected_ci_ids"]) == {"X", "L2", "L3", "L4", "L5"}
    assert result["count"] == 5


def test_ci_itself_never_in_affected_list():
    result = compute_blast_radius("B", CHAIN_FIXTURE, max_depth=5)
    assert "B" not in result["affected_ci_ids"]


def test_deterministic_same_input_same_output():
    r1 = compute_blast_radius("A", CHAIN_FIXTURE, max_depth=3)
    r2 = compute_blast_radius("A", CHAIN_FIXTURE, max_depth=3)
    assert r1 == r2
