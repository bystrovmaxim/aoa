# tests/graph_logical_contract/test_logical_reliability.py

"""
Extra contract checks for the logical graph interchange layer (builder, reverse map, ids).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Catch regressions that single golden or spot tests miss: full reverse map coverage,
degenerate G0 inputs, attribute propagation on reverse edges, and vertex-id edge cases.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from action_machine.graph.logical import (
    REVERSE_EDGE_MAP,
    REVERSE_EDGE_STEREOTYPE,
    LogicalEdge,
    build_from_g0_input,
    reverse_direct_edge,
    split_checker_vertex_id,
    split_host_element_vertex_id,
)


def test_build_from_g0_input_missing_top_level_key() -> None:
    with pytest.raises(KeyError):
        build_from_g0_input({"domains": [], "actions": []})


def test_build_from_g0_input_empty_lists() -> None:
    vertices, edges = build_from_g0_input({"domains": [], "actions": [], "roles": []})
    assert vertices == []
    assert edges == []


def test_build_from_g0_input_rejects_duplicate_domain_id() -> None:
    dup = "d1"
    inp = {
        "domains": [
            {"id": dup, "display_name": "D1"},
            {"id": dup, "display_name": "D2"},
        ],
        "actions": [],
        "roles": [],
    }
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_from_g0_input(inp)


def test_build_from_g0_input_rejects_duplicate_action_id() -> None:
    dup = "a1"
    inp = {
        "domains": [{"id": "d1", "display_name": "D"}],
        "actions": [
            {"id": dup, "display_name": "A1", "domain_id": "d1"},
            {"id": dup, "display_name": "A2", "domain_id": "d1"},
        ],
        "roles": [],
    }
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_from_g0_input(inp)


def test_build_from_g0_input_rejects_duplicate_role_id() -> None:
    dup = "r1"
    inp = {
        "domains": [{"id": "d1", "display_name": "D"}],
        "actions": [{"id": "a1", "display_name": "A", "domain_id": "d1"}],
        "roles": [
            {"id": dup, "display_name": "R1", "assigned_action_id": "a1"},
            {"id": dup, "display_name": "R2", "assigned_action_id": "a1"},
        ],
    }
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_from_g0_input(inp)


def test_build_from_g0_input_rejects_id_collision_across_kinds() -> None:
    shared = "same.id.X"
    inp = {
        "domains": [{"id": shared, "display_name": "D"}],
        "actions": [{"id": shared, "display_name": "A", "domain_id": shared}],
        "roles": [],
    }
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_from_g0_input(inp)


def test_build_from_g0_input_runtime_error_when_reverse_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_machine.graph.logical import g0_builder

    monkeypatch.setattr(g0_builder, "reverse_direct_edge", lambda _e: None)
    inp = {
        "domains": [{"id": "d1", "display_name": "D"}],
        "actions": [{"id": "a1", "display_name": "A", "domain_id": "d1"}],
        "roles": [],
    }
    with pytest.raises(RuntimeError, match="internal error: BELONGS_TO"):
        g0_builder.build_from_g0_input(inp)


def test_reverse_direct_edge_runtime_when_stereotype_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_machine.graph.logical import reverse_edge

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
    direct = LogicalEdge(
        source_id="a",
        target_id="b",
        edge_type="BELONGS_TO",
        stereotype="Aggregation",
        category="direct",
        is_dag=False,
        attributes={},
    )
    with pytest.raises(RuntimeError, match="missing REVERSE_EDGE_STEREOTYPE"):
        reverse_edge.reverse_direct_edge(direct)


def test_build_from_g0_input_counts_small_bundle() -> None:
    inp = {
        "domains": [{"id": "d1", "display_name": "D"}],
        "actions": [{"id": "a1", "display_name": "A", "domain_id": "d1"}],
        "roles": [{"id": "r1", "display_name": "R", "assigned_action_id": "a1"}],
    }
    vertices, edges = build_from_g0_input(inp)
    assert len(vertices) == 3
    assert len(edges) == 4
    assert sum(1 for e in edges if e.category == "direct") == 2
    assert sum(1 for e in edges if e.category == "reverse") == 2


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
    direct = LogicalEdge(
        source_id="src",
        target_id="tgt",
        edge_type=forward_type,
        stereotype="ForwardPlaceholder",
        category="direct",
        is_dag=True,
        attributes={"marker": 1},
    )
    rev = reverse_direct_edge(direct)
    assert rev is not None
    assert rev.source_id == "tgt"
    assert rev.target_id == "src"
    assert rev.edge_type == expected_reverse_type
    assert rev.stereotype == expected_rev_st
    assert rev.category == "reverse"
    assert rev.is_dag is False
    assert rev.attributes == {"marker": 1}


def test_reverse_direct_edge_returns_none_for_unknown_forward_type() -> None:
    direct = LogicalEdge(
        source_id="a",
        target_id="b",
        edge_type="NOT_A_CANONICAL_EDGE_TYPE",
        stereotype="X",
        category="direct",
        is_dag=False,
        attributes={},
    )
    assert reverse_direct_edge(direct) is None


def test_reverse_direct_edge_returns_none_when_already_reverse() -> None:
    edge = LogicalEdge(
        source_id="a",
        target_id="b",
        edge_type="CONTAINS",
        stereotype="Aggregation",
        category="reverse",
        is_dag=False,
        attributes={},
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
