# tests/scenarios/intents_with_runtime/test_role_graph_inspectors.py
"""Smoke tests for role topology facets on the built coordinator graph."""

from __future__ import annotations

from action_machine.runtime.machines.core_action_machine import CoreActionMachine


def test_default_coordinator_emits_role_mode_and_role_class_nodes() -> None:
    coord = CoreActionMachine.create_coordinator()
    role_mode_nodes = coord.get_nodes_by_type("role_mode")
    role_class_nodes = coord.get_nodes_by_type("role_class")
    assert len(role_mode_nodes) >= 1
    assert len(role_class_nodes) >= 1


def test_order_roles_present_and_requires_role_edges_exist() -> None:
    """Order*Role fixtures load MRO chain; graph has role_class + requires_role."""
    import tests.scenarios.intents_with_runtime.test_role_checker_pr2 as _pr2  # noqa: F401

    coord = CoreActionMachine.create_coordinator()
    names = [n["name"] for n in coord.get_nodes_by_type("role_class")]
    assert any("OrderManagerRole" in n for n in names), names
    assert any("OrderCreatorRole" in n for n in names), names
    assert any("OrderViewerRole" in n for n in names), names

    g = coord.get_graph()
    edge_types = {
        g.get_edge_data(e[0], e[1])["edge_type"]
        for e in g.edge_list()
    }
    assert "requires_role" in edge_types
