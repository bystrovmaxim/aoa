# src/action_machine/model/graph_model/action_graph_node_inspector.py
"""
ActionGraphNodeInspector — graph-node contributor for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseAction`` strict subclass tree and emits one :class:`ActionGraphNode` per
visited concrete/abstract subtype, plus one :class:`~graph.regular_aspect_graph_node.RegularAspectGraphNode`
per ``@regular_aspect``, one :class:`~graph.summary_aspect_graph_node.SummaryAspectGraphNode` per
``@summary_aspect``, one :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`
per checker on each regular aspect (via ``_checker_meta``), with ``COMPOSITION`` edges from each :class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode` to its checker nodes, one :class:`~graph.compensator_graph_node.CompensatorGraphNode` per
``@compensate``, and one :class:`~graph.error_handler_graph_node.ErrorHandlerGraphNode` per
``@on_error`` method declared on that class (own ``vars`` only; see
:meth:`IntentIntrospection.collect_own_class_callables_by_callable_kind`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction  (root axis)
              │
              v
    each loaded strict subclass ``cls`` emits ``ActionGraphNode``, ``RegularAspectGraphNode`` rows (each with ``COMPOSITION`` edges to their ``Checker`` nodes), ``SummaryAspectGraphNode``, flat ``CheckerGraphNode`` list (from each aspect's :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes`), compensators, and error handlers.
    when ``issubclass(cls, BaseAction)``
"""

from __future__ import annotations

from typing import Any

from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .action_graph_node import ActionGraphNode


class ActionGraphNodeInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ActionGraphNode`` rows for visited ``BaseAction`` classes.
    CONTRACT: Root axis ``BaseAction`` from ``BaseGraphNodeInspector[BaseAction[Any, Any]]``; one ``ActionGraphNode`` per visited ``BaseAction`` type, plus ``RegularAspectGraphNode`` (with ``COMPOSITION`` edges to checkers) / ``SummaryAspectGraphNode`` / ``CheckerGraphNode`` / ``CompensatorGraphNode`` / ``ErrorHandlerGraphNode`` for each own-class ``@regular_aspect`` / ``@summary_aspect`` / checker row / ``@compensate`` / ``@on_error`` method.
    INVARIANTS: Other intents stay on facet inspectors only; this inspector emits aspect, checker, compensator, and error-handler interchange rows for actions. Checker vertices are flattened from :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` on each ``RegularAspectGraphNode`` (see :class:`~graph.base_graph_node.BaseGraphNode`).
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if not (isinstance(cls, type) and issubclass(cls, BaseAction)):
            return []
        action_node = ActionGraphNode(cls)
        return [
            action_node
        ]
