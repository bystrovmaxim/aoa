# src/action_machine/model/graph_model/action_graph_node_inspector.py
"""
ActionGraphNodeInspector — graph-node contributor for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseAction`` strict subclass tree and emits one :class:`ActionGraphNode` per
visited concrete/abstract subtype, plus one :class:`~graph.regular_aspect_graph_node.RegularAspectGraphNode`
per ``@regular_aspect``, one :class:`~graph.summary_aspect_graph_node.SummaryAspectGraphNode` per
``@summary_aspect``, and one :class:`~graph.compensator_graph_node.CompensatorGraphNode` per
``@compensate``, and one :class:`~graph.error_handler_graph_node.ErrorHandlerGraphNode` per
``@on_error`` method declared on that class (own ``vars`` only; see
:meth:`IntentIntrospection.collect_own_class_callables_by_callable_kind`). The ``BaseAction`` axis
itself is excluded via
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`
so the abstract root does not emit an interchange row.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction  (root axis, skipped in walk)
              │
              v
    each loaded strict subclass ``cls``  ->  ``[ActionGraphNode(cls), *RegularAspectGraphNode(...), *SummaryAspectGraphNode(...), *CompensatorGraphNode(...), *ErrorHandlerGraphNode(...)]``
    when ``issubclass(cls, BaseAction)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_action import BaseAction
from action_machine.introspection_tools import CallableKind, IntentIntrospection, TypeIntrospection
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .action_graph_node import ActionGraphNode
from .compensator_graph_node import CompensatorGraphNode
from .error_handler_graph_node import ErrorHandlerGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode


class ActionGraphNodeInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ActionGraphNode`` rows for every loaded strict ``BaseAction`` subclass (not the root axis).
    CONTRACT: Root axis ``BaseAction`` from ``BaseGraphNodeInspector[BaseAction[Any, Any]]``; one ``ActionGraphNode`` per visited strict ``BaseAction`` subtype (root excluded), plus ``RegularAspectGraphNode`` / ``SummaryAspectGraphNode`` / ``CompensatorGraphNode`` / ``ErrorHandlerGraphNode`` for each own-class ``@regular_aspect`` / ``@summary_aspect`` / ``@compensate`` / ``@on_error`` method.
    INVARIANTS: Other intents stay on facet inspectors only; this inspector emits aspect, compensator, and error-handler interchange rows for actions.
    AI-CORE-END
    """

    def _graph_node_walk_excluded_types(self) -> frozenset[type]:
        return frozenset({BaseAction})

    @staticmethod
    def _regular_aspect_graph_nodes_for_class(action_cls: type) -> list[RegularAspectGraphNode]:
        """Interchange nodes for each own-class ``@regular_aspect`` on ``action_cls``."""
        return [
            RegularAspectGraphNode(aspect_callable)
            for aspect_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
                action_cls,
                CallableKind.REGULAR_ASPECT,
            )
        ]

    @staticmethod
    def _summary_aspect_graph_nodes_for_class(action_cls: type) -> list[SummaryAspectGraphNode]:
        """Interchange nodes for each own-class ``@summary_aspect`` on ``action_cls``."""
        return [
            SummaryAspectGraphNode(aspect_callable)
            for aspect_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
                action_cls,
                CallableKind.SUMMARY_ASPECT,
            )
        ]

    @staticmethod
    def _compensator_graph_nodes_for_class(action_cls: type) -> list[CompensatorGraphNode]:
        """Interchange nodes for each own-class ``@compensate`` on ``action_cls``."""
        return [
            CompensatorGraphNode(compensator_callable)
            for compensator_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
                action_cls,
                CallableKind.COMPENSATE,
            )
        ]

    @staticmethod
    def _error_handler_graph_nodes_for_class(action_cls: type) -> list[ErrorHandlerGraphNode]:
        """Interchange nodes for each own-class ``@on_error`` on ``action_cls``."""
        return [
            ErrorHandlerGraphNode(handler_callable)
            for handler_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
                action_cls,
                CallableKind.ON_ERROR,
            )
        ]

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if not (isinstance(cls, type) and issubclass(cls, BaseAction)):
            return []
        return [
            ActionGraphNode(cls),
            *self._regular_aspect_graph_nodes_for_class(cls),
            *self._summary_aspect_graph_nodes_for_class(cls),
            *self._compensator_graph_nodes_for_class(cls),
            *self._error_handler_graph_nodes_for_class(cls),
        ]
