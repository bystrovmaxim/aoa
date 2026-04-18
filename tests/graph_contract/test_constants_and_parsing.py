# tests/graph_contract/test_constants_and_parsing.py

"""
Unit tests: ``VERTEX_TYPES``, ``REVERSE_EDGE_MAP``, vertex-id parsing, ``reverse_direct_edge``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock graph interchange constants and pure helpers independent of ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``REVERSE_EDGE_MAP`` must be injective on keys and values must differ from keys.
"""

from __future__ import annotations

import pytest

from action_machine.graph import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
    REVERSE_EDGE_MAP,
    REVERSE_EDGE_STEREOTYPE,
    VERTEX_TYPES,
    GraphEdge,
    reverse_direct_edge,
    split_checker_vertex_id,
    split_host_element_vertex_id,
)


def test_vertex_types_contains_core_kinds() -> None:
    assert "Action" in VERTEX_TYPES
    assert "domain" in VERTEX_TYPES
    assert "checker" in VERTEX_TYPES
    assert "lifecycle_state_initial" in VERTEX_TYPES
    assert "params_schema" in VERTEX_TYPES
    assert len(VERTEX_TYPES) == 20


def test_reverse_edge_stereotype_covers_all_reversible_forwards() -> None:
    assert set(REVERSE_EDGE_STEREOTYPE.keys()) == set(REVERSE_EDGE_MAP.keys())


def test_reverse_edge_map_matches_adr() -> None:
    assert REVERSE_EDGE_MAP["BELONGS_TO"] == "CONTAINS"
    assert REVERSE_EDGE_MAP["ASSIGNED_TO"] == "REQUIRES_ROLE"
    assert REVERSE_EDGE_MAP["DEPENDS_ON"] == "DEPENDED_BY"
    assert REVERSE_EDGE_MAP["CONNECTS_TO"] == "SERVES"
    keys = set(REVERSE_EDGE_MAP.keys())
    values = set(REVERSE_EDGE_MAP.values())
    assert keys.isdisjoint(values)
    for k, v in REVERSE_EDGE_MAP.items():
        assert k != v


def test_ownership_and_internal_disjoint_from_autonomous_reversibles() -> None:
    rev_keys = set(REVERSE_EDGE_MAP.keys())
    assert OWNERSHIP_EDGE_TYPES.isdisjoint(rev_keys)
    assert INTERNAL_EDGE_TYPES.isdisjoint(rev_keys)


def test_dag_edge_types_subset_of_reversible_or_distinct() -> None:
    assert set(REVERSE_EDGE_MAP.keys()) >= DAG_EDGE_TYPES


def test_split_checker_vertex_id_ok() -> None:
    vid = "myapp.actions.CreateOrderAction.validate_data_aspect:txn_id"
    host, method, field = split_checker_vertex_id(vid)
    assert host == "myapp.actions.CreateOrderAction"
    assert method == "validate_data_aspect"
    assert field == "txn_id"


@pytest.mark.parametrize(
    "bad",
    [
        "no.colon.here",
        "two:colons:here",
        ":onlyfield",
        "onlyhost:",
    ],
)
def test_split_checker_vertex_id_rejects(bad: str) -> None:
    with pytest.raises(ValueError):
        split_checker_vertex_id(bad)


def test_split_host_element_vertex_id_ok() -> None:
    host, element = split_host_element_vertex_id("myapp.actions.CreateOrderAction.validate_data_aspect")
    assert host == "myapp.actions.CreateOrderAction"
    assert element == "validate_data_aspect"


def test_split_host_element_vertex_id_rejects_colon() -> None:
    with pytest.raises(ValueError):
        split_host_element_vertex_id("host.method:field")


def test_reverse_assigned_to_uses_access_stereotype_on_reverse() -> None:
    direct = GraphEdge(
        source_id="pkg.roles.R",
        target_id="pkg.actions.A",
        edge_type="ASSIGNED_TO",
        stereotype="Assignment",
        category="direct",
        is_dag=False,
        attributes={},
    )
    rev = reverse_direct_edge(direct)
    assert rev is not None
    assert rev.edge_type == "REQUIRES_ROLE"
    assert rev.stereotype == "Access"


def test_reverse_direct_edge_belongs_to() -> None:
    direct = GraphEdge(
        source_id="pkg.actions.A",
        target_id="pkg.domains.D",
        edge_type="BELONGS_TO",
        stereotype="Aggregation",
        category="direct",
        is_dag=False,
        attributes={},
    )
    rev = reverse_direct_edge(direct)
    assert rev is not None
    assert rev.source_id == "pkg.domains.D"
    assert rev.target_id == "pkg.actions.A"
    assert rev.edge_type == "CONTAINS"
    assert rev.category == "reverse"
    assert rev.is_dag is False


def test_reverse_direct_edge_returns_none_for_ownership() -> None:
    own = GraphEdge(
        source_id="pkg.actions.A",
        target_id="pkg.aspects.X",
        edge_type="HAS_ASPECT",
        stereotype="Composition",
        category="ownership",
        is_dag=False,
        attributes={},
    )
    assert reverse_direct_edge(own) is None


def test_reverse_direct_edge_returns_none_for_internal() -> None:
    internal = GraphEdge(
        source_id="pkg.checkers.C",
        target_id="pkg.aspects.X",
        edge_type="CHECKS_ASPECT",
        stereotype="Influence",
        category="internal",
        is_dag=False,
        attributes={},
    )
    assert reverse_direct_edge(internal) is None
