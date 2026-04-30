# src/action_machine/graph_model/edges/required_context_graph_edge.py
"""
RequiredContextGraphEdge — COMPOSITION from RegularAspect → RequiredContext interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Typed alternative to composing a generic :class:`~graph.composition_graph_edge.CompositionGraphEdge`
with ``edge_name`` ``required_context`` and dot-path ``key`` in ``properties`` toward a
:class:`~action_machine.graph_model.nodes.required_context_graph_node.RequiredContextGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──required_context──►  RequiredContextGraphNode (``properties['key']``)

Factory helpers (:meth:`RequiredContextGraphEdge.required_context_nodes_for_aspect`,
:meth:`RequiredContextGraphEdge.get_required_context_edges`) resolve ``@context_requires`` keys on the aspect
callable and emit one typed edge per companion vertex.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.graph_model.nodes.required_context_graph_node import RequiredContextGraphNode
from action_machine.intents.context_requires.context_requires_resolver import (
    ContextRequiresResolver,
)
from graph.composition_graph_edge import CompositionGraphEdge


class RequiredContextGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect → one ``@context_requires`` slot vertex.
    CONTRACT: ``edge_name`` literal ``required_context``; ``properties['key']`` from ``required_context_node.node_obj.context_key``; ``is_dag`` False; source vertex is identified by caller-provided ``source_node_id`` / ``source_node_type``.
    FACTORY: ``required_context_nodes_for_aspect`` builds companions from ``ContextRequiresResolver``; ``get_required_context_edges`` attaches one edge per node (caller supplies ``aspect_node_type``).
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node_type: str,
        required_context_node: RequiredContextGraphNode,
    ) -> None:
        super().__init__(
            edge_name="required_context",
            is_dag=False,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=None,
            target_node_id=required_context_node.node_id,
            target_node_type=required_context_node.node_type,
            target_node=required_context_node,
            properties={"key": required_context_node.node_obj.context_key},
        )

    @staticmethod
    def required_context_nodes_for_aspect(
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
    ) -> list[RequiredContextGraphNode]:
        """One :class:`RequiredContextGraphNode` per ``@context_requires`` dot-path key (sorted)."""
        keys = ContextRequiresResolver.resolve_required_context_keys(aspect_callable)
        return [RequiredContextGraphNode(aspect_callable, _action_cls, k) for k in keys]

    @staticmethod
    def get_required_context_edges(
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
        aspect_node_id: str,
        aspect_node_type: str,
    ) -> list[RequiredContextGraphEdge]:
        """Typed ``required_context`` edges for every companion row on ``aspect_callable``."""
        return [
            RequiredContextGraphEdge(
                source_node_id=aspect_node_id,
                source_node_type=aspect_node_type,
                required_context_node=rn,
            )
            for rn in RequiredContextGraphEdge.required_context_nodes_for_aspect(
                aspect_callable,
                _action_cls,
            )
        ]
