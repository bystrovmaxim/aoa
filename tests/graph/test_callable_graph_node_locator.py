# tests/graph/test_callable_graph_node_locator.py
"""Action graph node callable edge behavior."""

from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.edges.compensator_graph_edge import (
    CompensatorGraphEdge,
)
from action_machine.model.graph_model.edges.error_handler_graph_edge import (
    ErrorHandlerGraphEdge,
)
from action_machine.model.graph_model.edges.regular_aspect_graph_edge import (
    RegularAspectGraphEdge,
)
from action_machine.model.graph_model.edges.summary_aspect_graph_edge import (
    SummaryAspectGraphEdge,
)
from tests.scenarios.domain_model.child_action import ChildAction
from tests.scenarios.domain_model.ping_action import PingAction


def test_get_summary_aspect_builds_edges() -> None:
    node = ActionGraphNode(PingAction)

    assert SummaryAspectGraphEdge.get_summary_aspect_edges(node, PingAction) == node.summary_aspect


def test_get_regular_aspect_builds_edges_with_target_nodes() -> None:
    node = ActionGraphNode(ChildAction)

    edges = RegularAspectGraphEdge.get_regular_aspect_edges(node, ChildAction)

    assert edges == node.regular_aspect
    assert [edge.target_node for edge in edges] == node.get_companion_nodes()[: len(edges)]


def test_get_compensator_edges_builds_edges() -> None:
    node = ActionGraphNode(ChildAction)

    assert CompensatorGraphEdge.get_compensator_edges(node, ChildAction) == node.compensator_graph


def test_get_error_handler_edges_builds_edges() -> None:
    node = ActionGraphNode(ChildAction)

    assert ErrorHandlerGraphEdge.get_on_error_handlers_edges(node, ChildAction) == node.error_handler_graph
