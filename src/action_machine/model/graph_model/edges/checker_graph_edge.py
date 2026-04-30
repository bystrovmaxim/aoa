# src/action_machine/model/graph_model/edges/checker_graph_edge.py
"""
CheckerGraphEdge — COMPOSITION from RegularAspect → Checker interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the typed :class:`CheckerGraphEdge` for each :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`
under a :class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode`
(``edge_name`` ``@result_checker``, ``is_dag`` False), instead of synthesizing a bare
:class:`~graph.composition_graph_edge.CompositionGraphEdge`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──@result_checker──►  CheckerGraphNode

Factory helpers (:meth:`CheckerGraphEdge.checkers_for_method`, :meth:`CheckerGraphEdge.edges_for_aspect`)
read ``_checker_meta`` on the aspect callable and attach :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`
targets to each typed edge.

"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from graph.base_intent_inspector import BaseIntentInspector
from graph.composition_graph_edge import CompositionGraphEdge


class CheckerGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect vertex → checker row.
    CONTRACT: ``edge_name`` literal ``@result_checker``; ``is_dag`` False; ``source_node`` left unset (``None``) so frozen edge equality does not recurse through the host :class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode`; ``target_node`` is the checker vertex.
    FACTORY: ``checkers_for_method`` parses ``_checker_meta``; ``edges_for_aspect`` materializes checker rows and attaches one edge per row (caller supplies ``aspect_vertex_type``).
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        checker_node: CheckerGraphNode,
        source_node_id: str,
        source_node_type: str,
    ) -> None:
        super().__init__(
            edge_name="@result_checker",
            is_dag=False,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=None,
            target_node_id=checker_node.node_id,
            target_node_type=checker_node.node_type,
            target_node=checker_node,
        )

    @staticmethod
    def checkers_for_method(method: Any) -> list[dict[str, Any]]:
        """Checker metadata dicts from ``_checker_meta`` on this aspect method (unwraps ``property``)."""
        func = BaseIntentInspector._unwrap_declaring_class_member(method)
        if not callable(func):
            return []
        raw = getattr(func, "_checker_meta", None)
        if raw is None or isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            return []
        out: list[dict[str, Any]] = []
        for row in raw:
            if isinstance(row, Mapping):
                out.append(dict(row))
        return out

    @staticmethod
    def edges_for_aspect(
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
        aspect_node_id: str,
        aspect_vertex_type: str,
    ) -> list[CheckerGraphEdge]:
        """Typed ``@result_checker`` edges from ``_checker_meta`` on ``aspect_callable``."""
        edges: list[CheckerGraphEdge] = []
        for row in CheckerGraphEdge.checkers_for_method(aspect_callable):
            cc = row.get("checker_class")
            if not isinstance(cc, type):
                continue
            raw = row.get("field_name", "")
            field = raw if isinstance(raw, str) else str(raw)
            extra = {k: v for k, v in row.items() if k not in ("checker_class", "field_name", "required")}
            chk = CheckerGraphNode(
                aspect_callable=aspect_callable,
                _action_cls=_action_cls,
                checker_class=cc,
                field_name=field,
                required=bool(row.get("required", False)),
                properties=extra if extra else None,
            )
            edges.append(
                CheckerGraphEdge(
                    checker_node=chk,
                    source_node_id=aspect_node_id,
                    source_node_type=aspect_vertex_type,
                ),
            )
        return edges
