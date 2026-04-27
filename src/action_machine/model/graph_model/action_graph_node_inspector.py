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

from typing import Any, cast

from action_machine.introspection_tools import CallableKind, IntentIntrospection
from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .action_graph_node import ActionGraphNode
from .checker_graph_node import CheckerGraphNode
from .compensator_graph_node import CompensatorGraphNode
from .error_handler_graph_node import ErrorHandlerGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode


class ActionGraphNodeInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ActionGraphNode`` rows for visited ``BaseAction`` classes.
    CONTRACT: Root axis ``BaseAction`` from ``BaseGraphNodeInspector[BaseAction[Any, Any]]``; one ``ActionGraphNode`` per visited ``BaseAction`` type, plus ``RegularAspectGraphNode`` (with ``COMPOSITION`` edges to checkers) / ``SummaryAspectGraphNode`` / ``CheckerGraphNode`` / ``CompensatorGraphNode`` / ``ErrorHandlerGraphNode`` for each own-class ``@regular_aspect`` / ``@summary_aspect`` / checker row / ``@compensate`` / ``@on_error`` method.
    INVARIANTS: Other intents stay on facet inspectors only; this inspector emits aspect, checker, compensator, and error-handler interchange rows for actions. Checker vertices are flattened from :attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` on each ``RegularAspectGraphNode`` (see :class:`~graph.base_graph_node.BaseGraphNode`).
    AI-CORE-END
    """

    @staticmethod
    def _regular_aspect_and_checker_graph_nodes_for_class(
        action_cls: type,
    ) -> tuple[list[RegularAspectGraphNode], list[CheckerGraphNode]]:
        """Return ``(regular_aspect_nodes, checker_nodes)`` for ``action_cls`` (checkers from each aspect's ``companion_nodes``)."""
        regular_out: list[RegularAspectGraphNode] = []
        all_checkers: list[CheckerGraphNode] = []
        for aspect_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
            action_cls,
            CallableKind.REGULAR_ASPECT,
        ):
            aspect_node = RegularAspectGraphNode(aspect_callable)
            regular_out.append(aspect_node)
            # Flatten companions: coordinator only sees ids from get_graph_nodes(), not nested lists.
            all_checkers.extend(cast(list[CheckerGraphNode], aspect_node.companion_nodes))
        return regular_out, all_checkers

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
        regular_aspects, regular_checkers = ActionGraphNodeInspector._regular_aspect_and_checker_graph_nodes_for_class(
            cls,
        )
        return [
            ActionGraphNode(cls),
            *regular_aspects,
            *self._summary_aspect_graph_nodes_for_class(cls),
            *regular_checkers,
            *self._compensator_graph_nodes_for_class(cls),
            *self._error_handler_graph_nodes_for_class(cls),
        ]
