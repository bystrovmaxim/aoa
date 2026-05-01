# tests/graph/test_checker_graph_edge.py
"""Constructor tests for :class:`~action_machine.graph_model.edges.checker_graph_edge.CheckerGraphEdge`."""

from __future__ import annotations

from action_machine.graph_model.edges.checker_graph_edge import CheckerGraphEdge
from action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from graph.edge_relationship import COMPOSITION
from tests.scenarios.domain_model.child_action import ChildAction


def test_checker_graph_edge_links_aspect_id_to_checker_target() -> None:
    aspect = RegularAspectGraphNode(ChildAction.process_aspect, ChildAction)
    checker = aspect.get_checker_graph_nodes()[0]
    edge = CheckerGraphEdge(
        checker_node=checker,
        source_node_id=aspect.node_id,
        aspect_vertex_type=aspect.node_type,
    )
    assert edge.edge_name == "@result_checker"
    assert edge.edge_relationship is COMPOSITION
    assert edge.source_node is None
    assert edge.target_node == checker
