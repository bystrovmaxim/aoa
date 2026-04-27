# src/action_machine/model/graph_model/callable_graph_node_locator.py
"""CallableGraphNodeLocator — builds graph edges to callable-owned graph nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.intents.aspects.regular_aspect_intent_resolver import (
    RegularAspectIntentResolver,
)
from action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)
from action_machine.intents.compensate.compensate_intent_resolver import (
    CompensateIntentResolver,
)
from action_machine.intents.on_error.on_error_intent_resolver import (
    OnErrorIntentResolver,
)
from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge

from .compensator_graph_node import CompensatorGraphNode
from .error_handler_graph_node import ErrorHandlerGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode


class CallableGraphNodeLocator:
    """
    AI-CORE-BEGIN
    ROLE: Build composition edges from a source graph node to callable-owned graph nodes.
    CONTRACT: Materializes target graph nodes through the provided factory and attaches them to each edge.
    INVARIANTS: Preserves callable order and does not inspect intent metadata itself.
    AI-CORE-END
    """

    @staticmethod
    def get_regular_aspect_edges(
        source_node: BaseGraphNode[type[BaseAction[Any, Any]]],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return regular aspect composition edges for ``action_cls``."""
        return CallableGraphNodeLocator._get_callable_edges(
            source_node,
            RegularAspectGraphNode,
            RegularAspectIntentResolver.resolve_regular_aspects(action_cls),
        )

    @staticmethod
    def get_summary_aspect_edges(
        source_node: BaseGraphNode[type[BaseAction[Any, Any]]],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return summary aspect composition edges for ``action_cls``."""
        return CallableGraphNodeLocator._get_callable_edges(
            source_node,
            SummaryAspectGraphNode,
            SummaryAspectIntentResolver.resolve_summary_aspects(action_cls),
        )

    @staticmethod
    def get_compensator_edges(
        source_node: BaseGraphNode[type[BaseAction[Any, Any]]],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return compensator composition edges for ``action_cls``."""
        return CallableGraphNodeLocator._get_callable_edges(
            source_node,
            CompensatorGraphNode,
            CompensateIntentResolver.resolve_compensators(action_cls),
        )

    @staticmethod
    def get_error_handler_edges(
        source_node: BaseGraphNode[type[BaseAction[Any, Any]]],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return error handler composition edges for ``action_cls``."""
        return CallableGraphNodeLocator._get_callable_edges(
            source_node,
            ErrorHandlerGraphNode,
            OnErrorIntentResolver.resolve_error_handlers(action_cls),
        )

    @staticmethod
    def _get_callable_edges(
        source_node: BaseGraphNode[Any],
        graph_node_factory: Callable[[Any], BaseGraphNode[Any]],
        graph_node_objects: list[Any],
    ) -> list[CompositionGraphEdge]:
        """Return ``COMPOSITION`` edges from ``source_node`` to callable graph nodes."""
        edges: list[CompositionGraphEdge] = []
        for graph_node_obj in graph_node_objects:
            graph_node = graph_node_factory(graph_node_obj)
            edges.append(
                CompositionGraphEdge(
                    edge_name=graph_node.label,
                    is_dag=False,
                    source_node_id=source_node.node_id,
                    source_node_type=source_node.node_type,
                    source_node=source_node,
                    target_node_id=graph_node.node_id,
                    target_node_type=graph_node.node_type,
                    target_node=graph_node,
                ),
            )
        return edges
