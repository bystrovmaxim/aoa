# src/action_machine/model/graph_model/regular_aspect_graph_node.py
"""
RegularAspectGraphNode — interchange node for a ``@regular_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one regular
aspect **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``RegularAspect``, ``label`` is the method name, ``properties`` empty.
The node **self-inspects** ``_checker_meta`` on ``aspect_func``, materializes
:class:`CheckerGraphNode` companions, and emits ``COMPOSITION`` edges from this aspect to each checker.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Callable[..., Any]   unbound/bound aspect method  ->  ``node_obj``
              │
              v
    RegularAspectGraphNode(aspect_func)  reads ``_checker_meta``, sets ``edges`` + ``companion_checkers``
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar

from action_machine.introspection_tools import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_intent_inspector import BaseIntentInspector
from graph.edge_relationship import COMPOSITION

from .checker_graph_node import CheckerGraphNode


@dataclass(init=False, frozen=True)
class RegularAspectGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a regular aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``RegularAspect``; empty ``properties``; ``edges`` / :attr:`companion_checkers` derived from ``_checker_meta`` on ``aspect_func`` (see :meth:`checkers_for_method`).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "RegularAspect"
    companion_checkers: tuple[CheckerGraphNode, ...] = field(init=False, default_factory=tuple)

    def __init__(self, aspect_func: Callable[..., Any]) -> None:
        checkers = RegularAspectGraphNode._checker_nodes_for_aspect(aspect_func)
        action_cls = TypeIntrospection.owner_type_for_method(aspect_func)
        method_name = TypeIntrospection.unwrapped_callable_name(aspect_func)
        action_id = TypeIntrospection.full_qualname(action_cls)
        node_id = f"{action_id}:{method_name}"
        edges = RegularAspectGraphNode._composition_edges_to_checkers(aspect_func, node_id, checkers)
        super().__init__(
            node_id=node_id,
            node_type=RegularAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={},
            edges=edges,
            node_obj=aspect_func,
        )
        object.__setattr__(self, "companion_checkers", tuple(checkers))

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
    def _checker_nodes_for_aspect(aspect_callable: Callable[..., Any]) -> list[CheckerGraphNode]:
        nodes: list[CheckerGraphNode] = []
        for row in RegularAspectGraphNode.checkers_for_method(aspect_callable):
            cc = row.get("checker_class")
            if not isinstance(cc, type):
                continue
            raw = row.get("field_name", "")
            field = raw if isinstance(raw, str) else str(raw)
            extra = {k: v for k, v in row.items() if k not in ("checker_class", "field_name", "required")}
            nodes.append(
                CheckerGraphNode(
                    aspect_callable,
                    cc,
                    field,
                    required=bool(row.get("required", False)),
                    properties=extra if extra else None,
                ),
            )
        return nodes

    @staticmethod
    def _composition_edges_to_checkers(
        aspect_callable: Callable[..., Any],
        aspect_node_id: str,
        checkers: list[CheckerGraphNode],
    ) -> list[BaseGraphEdge]:
        return [
            BaseGraphEdge(
                edge_name=f"checker:{ch.node_obj.field_name.strip() or '_'}",
                is_dag=False,
                source_node_id=aspect_node_id,
                source_node_type=RegularAspectGraphNode.NODE_TYPE,
                source_node_obj=aspect_callable,
                target_node_id=ch.node_id,
                target_node_type=CheckerGraphNode.NODE_TYPE,
                target_node_obj=ch.node_obj,
                edge_relationship=COMPOSITION,
            )
            for ch in checkers
        ]
