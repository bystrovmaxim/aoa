# tests/graph/test_required_context_graph_edge.py
"""Unit tests for typed :class:`~action_machine.graph_model.edges.required_context_graph_edge.RequiredContextGraphEdge`."""

from __future__ import annotations

from action_machine.graph_model.edges.required_context_graph_edge import RequiredContextGraphEdge
from action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.graph_model.nodes.required_context_graph_node import RequiredContextGraphNode
from graph.edge_relationship import COMPOSITION
from tests.graph.test_interchange_nodes import _RegularAspectWithCtx


def test_required_context_graph_edge_matches_plain_composition_contract() -> None:
    aspect = RegularAspectGraphNode(_RegularAspectWithCtx.step_aspect, _RegularAspectWithCtx)
    ctx_vertex = RequiredContextGraphNode(
        _RegularAspectWithCtx.step_aspect,
        _RegularAspectWithCtx,
        "request.trace_id",
    )
    edge = RequiredContextGraphEdge(
        source_node_id=aspect.node_id,
        aspect_vertex_type=aspect.node_type,
        required_context_node=ctx_vertex,
    )
    assert edge.edge_name == "@required_context"
    assert edge.edge_relationship is COMPOSITION
    assert edge.properties["key"] == ctx_vertex.node_obj.context_key
    assert edge.target_node == ctx_vertex
    assert edge.source_node is None
