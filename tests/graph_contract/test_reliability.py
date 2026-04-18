# tests/graph_contract/test_reliability.py

"""
Extra contract checks for the graph interchange layer (reverse map, ids).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Catch regressions: full reverse map coverage, attribute propagation on reverse
edges, and vertex-id edge cases.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from action_machine.graph import (
    REVERSE_EDGE_MAP,
    REVERSE_EDGE_STEREOTYPE,
    GraphEdge,
    reverse_direct_edge,
    split_checker_vertex_id,
    split_host_element_vertex_id,
)


def test_reverse_direct_edge_runtime_when_stereotype_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import action_machine.graph.reverse_edge as reverse_edge

    monkeypatch.setattr(
        reverse_edge,
        "REVERSE_EDGE_MAP",
        MappingProxyType({"BELONGS_TO": "CONTAINS"}),
    )
    monkeypatch.setattr(
        reverse_edge,
        "REVERSE_EDGE_STEREOTYPE",
        MappingProxyType({}),
    )
    direct = GraphEdge(
        source_id="a",
        target_id="b",
        edge_type="BELONGS_TO",
        stereotype="Aggregation",
        category="direct",
        is_dag=False,
        properties={},
    )
    with pytest.raises(RuntimeError, match="missing REVERSE_EDGE_STEREOTYPE"):
        reverse_edge.reverse_direct_edge(direct)


@pytest.mark.parametrize(
    ("forward_type", "expected_reverse_type", "expected_rev_st"),
    [
        (k, REVERSE_EDGE_MAP[k], REVERSE_EDGE_STEREOTYPE[k])
        for k in sorted(REVERSE_EDGE_MAP)
    ],
)
def test_reverse_direct_edge_matches_tables_for_all_reversible_types(
    forward_type: str,
    expected_reverse_type: str,
    expected_rev_st: str,
) -> None:
    direct = GraphEdge(
        source_id="src",
        target_id="tgt",
        edge_type=forward_type,
        stereotype="ForwardPlaceholder",
        category="direct",
        is_dag=True,
        properties={"marker": 1},
    )
    rev = reverse_direct_edge(direct)
    assert rev is not None
    assert rev.source_id == "tgt"
    assert rev.target_id == "src"
    assert rev.edge_type == expected_reverse_type
    assert rev.stereotype == expected_rev_st
    assert rev.category == "reverse"
    assert rev.is_dag is False
    assert rev.properties == {"marker": 1}


def test_reverse_direct_edge_returns_none_for_unknown_forward_type() -> None:
    direct = GraphEdge(
        source_id="a",
        target_id="b",
        edge_type="NOT_A_CANONICAL_EDGE_TYPE",
        stereotype="X",
        category="direct",
        is_dag=False,
        properties={},
    )
    assert reverse_direct_edge(direct) is None


def test_reverse_direct_edge_returns_none_when_already_reverse() -> None:
    edge = GraphEdge(
        source_id="a",
        target_id="b",
        edge_type="CONTAINS",
        stereotype="Aggregation",
        category="reverse",
        is_dag=False,
        properties={},
    )
    assert reverse_direct_edge(edge) is None


def test_reverse_stereotype_values_are_nonempty() -> None:
    for k, st in REVERSE_EDGE_STEREOTYPE.items():
        assert isinstance(st, str) and st.strip(), f"empty stereotype for {k!r}"


def test_split_checker_nested_qualname_before_colon() -> None:
    host, method, field = split_checker_vertex_id(
        "myapp.pkg.actions.CreateOrderAction.validate_aspect:amount_cents",
    )
    assert host == "myapp.pkg.actions.CreateOrderAction"
    assert method == "validate_aspect"
    assert field == "amount_cents"


def test_split_host_element_nested_qualname() -> None:
    host, element = split_host_element_vertex_id("myapp.pkg.actions.CreateOrderAction.summary_aspect")
    assert host == "myapp.pkg.actions.CreateOrderAction"
    assert element == "summary_aspect"


@pytest.mark.parametrize("bad", ["nodots", "", "only.dots."])
def test_split_host_element_rejects_missing_or_empty_parts(bad: str) -> None:
    with pytest.raises(ValueError):
        split_host_element_vertex_id(bad)
