# tests/graph/test_callable_graph_node_locator.py
"""Action graph node callable edge behavior."""

from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.edges.regular_aspect_graph_edge import (
    RegularAspectGraphEdge,
)
from tests.scenarios.domain_model.child_action import ChildAction
from tests.scenarios.domain_model.ping_action import PingAction


def test_get_summary_aspect_edges_builds_edges() -> None:
    node = ActionGraphNode(PingAction)

    assert ActionGraphNode.get_summary_aspect_edges(node, PingAction) == node.summary_aspect_edges


def test_get_regular_aspect_edges_builds_edges_with_target_nodes() -> None:
    node = ActionGraphNode(ChildAction)

    edges = RegularAspectGraphEdge.edges_from_regular_aspects(node, ChildAction)

    assert edges == node.regular_aspect_edges
    assert [edge.target_node for edge in edges] == node.get_companion_nodes()[: len(edges)]


def test_get_compensator_edges_builds_edges() -> None:
    node = ActionGraphNode(ChildAction)

    assert ActionGraphNode.get_compensator_edges(node, ChildAction) == node.compensator_graph_edges


def test_get_error_handler_edges_builds_edges() -> None:
    node = ActionGraphNode(ChildAction)

    assert ActionGraphNode.get_error_handler_edges(node, ChildAction) == node.error_handler_graph_edges
