# src/action_machine/graph_model/edges/checker_graph_edge.py
"""
CheckerGraphEdge — COMPOSITION from RegularAspect → Checker interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the typed :class:`CheckerGraphEdge` for each :class:`~action_machine.graph_model.nodes.checker_graph_node.CheckerGraphNode`
under a :class:`~action_machine.graph_model.nodes.regular_aspect_graph_node.RegularAspectGraphNode`
(``edge_name`` ``@result_checker``, ``is_dag`` False), instead of synthesizing a bare
:class:`~graph.composition_graph_edge.CompositionGraphEdge`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──@result_checker──►  CheckerGraphNode

    Factory helpers (:meth:`CheckerGraphEdge.checkers_for_method`, :meth:`CheckerGraphEdge.get_checker_edges`)
read ``_checker_meta`` on the aspect callable and attach :class:`~action_machine.graph_model.nodes.checker_graph_node.CheckerGraphNode`
targets to each typed edge.

"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from action_machine.graph_model.nodes.checker_graph_node import CheckerGraphNode
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class CheckerGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect vertex → checker row.
    CONTRACT: ``edge_name`` literal ``@result_checker``; ``is_dag`` False; ``target_node`` is the checker vertex.
    FACTORY: ``checkers_for_method`` parses ``_checker_meta``; ``get_checker_edges`` materializes checker rows wired to ``aspect_node``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        checker_node: CheckerGraphNode,
    ) -> None:
        super().__init__(
            edge_name="@result_checker",
            is_dag=False,
            target_node_id=checker_node.node_id,
            target_node=checker_node,
        )

    @staticmethod
    def checkers_for_method(method: Any) -> list[dict[str, Any]]:
        """Return normalized ``_checker_meta`` rows from method metadata."""
        func = TypeIntrospection.unwrap_declaring_class_member(method)
        raw = getattr(func, "_checker_meta", None) if callable(func) else None
        return CheckerGraphEdge._normalized_checker_meta_rows(raw)

    @staticmethod
    def get_checker_edges(
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
        _aspect_node: BaseGraphNode[Any],
    ) -> list[CheckerGraphEdge]:
        """Typed ``@result_checker`` edges from ``_checker_meta`` on ``aspect_callable``."""
        edges: list[CheckerGraphEdge] = []
        for row in CheckerGraphEdge.checkers_for_method(aspect_callable):
            checker_node = CheckerGraphEdge._build_checker_node(
                aspect_callable=aspect_callable,
                _action_cls=_action_cls,
                row=row,
            )
            if checker_node is None:
                continue
            edges.append(
                CheckerGraphEdge(
                    checker_node=checker_node,
                ),
            )
        return edges

    @staticmethod
    def _normalized_checker_meta_rows(raw: Any) -> list[dict[str, Any]]:
        """Normalize raw ``_checker_meta`` payload into plain mapping rows."""
        if raw is None or isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            return []
        out: list[dict[str, Any]] = []
        for row in raw:
            if isinstance(row, Mapping):
                out.append(dict(row))
        return out

    @staticmethod
    def _build_checker_node(
        *,
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
        row: dict[str, Any],
    ) -> CheckerGraphNode | None:
        """Build ``CheckerGraphNode`` from one normalized metadata row."""
        checker_class = row.get("checker_class")
        if not isinstance(checker_class, type):
            return None

        raw_field_name = row.get("field_name", "")
        field_name = raw_field_name if isinstance(raw_field_name, str) else str(raw_field_name)
        extra_props = {
            key: value
            for key, value in row.items()
            if key not in ("checker_class", "field_name", "required")
        }
        return CheckerGraphNode(
            aspect_callable=aspect_callable,
            _action_cls=_action_cls,
            checker_class=checker_class,
            field_name=field_name,
            required=bool(row.get("required", False)),
            properties=extra_props if extra_props else None,
        )
