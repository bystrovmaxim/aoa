# tests/scenarios/intents_with_runtime/test_role_graph_inspectors.py
"""Smoke tests for role topology facets on the built coordinator graph."""

from __future__ import annotations

from action_machine.runtime.machines.core import Core


def test_default_coordinator_emits_role_mode_and_role_class_nodes() -> None:
    """``@role_mode`` merges into the single ``ApplicationRole`` ``role_class`` vertex."""
    from action_machine.intents.auth.application_role import ApplicationRole

    coord = Core.create_coordinator()
    assert not coord.get_nodes_by_type("role_mode")
    role_class_nodes = coord.get_nodes_by_type("role_class")
    assert len(role_class_nodes) >= 1
    app_rows = [n for n in role_class_nodes if n["class_ref"] is ApplicationRole]
    assert app_rows, "expected ApplicationRole role_class node"
    snap = coord.get_snapshot(ApplicationRole, "role_mode")
    assert snap is not None
    rows = coord.hydrate_graph_node(dict(app_rows[0])).get("facet_rows") or {}
    assert "mode" in rows


def test_order_roles_present_and_requires_role_edges_exist() -> None:
    """Order*Role fixtures validate; graph exposes only anchor role_class + requires_role."""
    import tests.scenarios.intents_with_runtime.test_role_checker_pr2 as _pr2  # noqa: F401
    from action_machine.intents.auth.application_role import ApplicationRole

    coord = Core.create_coordinator()
    refs = {n["class_ref"] for n in coord.get_nodes_by_type("role_class")}
    assert refs == {ApplicationRole}, refs

    g = coord.facet_topology_copy()
    edge_types = {
        g.get_edge_data(e[0], e[1])["edge_type"]
        for e in g.edge_list()
    }
    assert "requires_role" in edge_types
