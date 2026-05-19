"""Regression: entity sidebar must not pick foreign Lifecycle rows via Domain (or other) hops."""

from __future__ import annotations

import networkx as nx

from aoa.maxitor.model.core.actions.left_sidebar_action import (
    _diagram_view_label,
    _lifecycle_nodes_for_entity,
    _lifecycle_state_machine_row_title,
)


def test_lifecycle_rows_only_follow_lifecycle_edges() -> None:
    """Two-hop Domain → Lifecycle must not count as belonging to the entity."""
    g = nx.DiGraph()
    g.add_node("entity", node_type="Entity", label="E")
    g.add_node("domain", node_type="Domain", label="D")
    g.add_node("own_lc", node_type="Lifecycle", label="lifecycle")
    g.add_node("stray_lc", node_type="Lifecycle", label="lifecycle")
    g.add_edge("entity", "own_lc", edge_name="lifecycle", is_dag=False)
    g.add_edge("entity", "domain", edge_name="domain", is_dag=True)
    g.add_edge("domain", "stray_lc", edge_name="field", is_dag=False)

    rows = _lifecycle_nodes_for_entity(g, "entity")
    assert rows == [("own_lc", "lifecycle")]


def test_fallback_direct_lifecycle_when_no_edge_name() -> None:
    """If ``edge_name`` is absent, still surface direct Lifecycle successors."""
    g = nx.DiGraph()
    g.add_node("entity", node_type="Entity", label="E")
    g.add_node("lc", node_type="Lifecycle", label="status")
    g.add_edge("entity", "lc")

    rows = _lifecycle_nodes_for_entity(g, "entity")
    assert rows == [("lc", "status")]


def test_diagram_view_label_idempotent() -> None:
    assert _diagram_view_label("Full graph") == "Full graph view"
    assert _diagram_view_label("Full graph view") == "Full graph view"


def test_lifecycle_state_machine_sidebar_title() -> None:
    assert _lifecycle_state_machine_row_title("lifecycle") == "Lifecycle view"
    assert (
        _lifecycle_state_machine_row_title("counterparty_linkage_lifecycle")
        == "Counterparty linkage lifecycle view"
    )
    assert (
        _lifecycle_state_machine_row_title("scheme_dispute_clock_lifecycle")
        == "Scheme dispute clock lifecycle view"
    )
    assert _lifecycle_state_machine_row_title("") == "Lifecycle view"
