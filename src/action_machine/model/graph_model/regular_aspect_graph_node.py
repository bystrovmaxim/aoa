# src/action_machine/model/graph_model/regular_aspect_graph_node.py
"""
RegularAspectGraphNode — interchange node for a ``@regular_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one regular
aspect **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``RegularAspect``, ``label`` is the method name; ``properties`` may carry ``description`` from
``RegularAspectIntentResolver.resolve_description`` when present.
The node **self-inspects** ``_checker_meta`` on ``aspect_func`` and ``@context_requires`` keys
(via :class:`~action_machine.intents.context_requires.context_requires_resolver.ContextRequiresResolver`),
materializes :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode` and
:class:`~action_machine.model.graph_model.required_context_graph_node.RequiredContextGraphNode` companions,
and emits ``COMPOSITION`` edges from this aspect to each checker and required-context slot row
(checkers: ``edge_name`` ``@result_checker``; required context: ``edge_name`` ``required_context``, dot-path key in ``properties['key']``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, cast

from action_machine.intents.aspects.regular_aspect_intent_resolver import RegularAspectIntentResolver
from action_machine.intents.context_requires.context_requires_resolver import (
    ContextRequiresResolver,
)
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_intent_inspector import BaseIntentInspector
from graph.composition_graph_edge import CompositionGraphEdge

from .checker_graph_node import CheckerGraphNode
from .required_context_graph_node import RequiredContextGraphNode


@dataclass(init=False, frozen=True)
class RegularAspectGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a regular aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``RegularAspect``; ``properties`` include ``description`` when ``RegularAspectIntentResolver.resolve_description(...)`` returns it; :attr:`checkers` / :attr:`required_context` and :attr:`companion_nodes` (``CheckerGraphNode`` and ``RequiredContextGraphNode`` rows) from ``_checker_meta`` and ``@context_requires`` on ``aspect_func`` (see :meth:`checkers_for_method`). :meth:`get_required_context_keys` is the ``frozenset`` of ``properties['key']`` on edges in :attr:`required_context`.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "RegularAspect"
    checkers: list[CompositionGraphEdge]
    required_context: list[CompositionGraphEdge]

    def __init__(self, aspect_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        method_name = TypeIntrospection.unwrapped_callable_name(aspect_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        node_id = f"{action_id}:{method_name}"
        checker_nodes = RegularAspectGraphNode._checker_nodes_for_aspect(aspect_func, _action_cls)
        checkers = RegularAspectGraphNode._composition_edges_to_checkers(aspect_func, node_id, checker_nodes)
        req_ctx_rows = RegularAspectGraphNode._required_context_nodes_for_aspect(aspect_func, _action_cls)
        required_context = RegularAspectGraphNode._composition_edges_to_required_context(
            aspect_func, node_id, req_ctx_rows,
        )
        desc = RegularAspectIntentResolver.resolve_description(aspect_func)
        super().__init__(
            node_id=node_id,
            node_type=RegularAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": desc} if desc is not None else {},
            node_obj=aspect_func,
        )
        object.__setattr__(self, "checkers", checkers)
        object.__setattr__(self, "required_context", required_context)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return checker and required-context composition edges materialized on this node."""
        return [*self.checkers, *self.required_context]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return checker and required-context companion nodes referenced by composition edges."""
        chk = [edge.target_node for edge in self.checkers if edge.target_node is not None]
        ctx = [edge.target_node for edge in self.required_context if edge.target_node is not None]
        return [*chk, *ctx]

    def get_checker_graph_nodes(self) -> list[CheckerGraphNode]:
        """Interchange checker vertices for this aspect (composition targets on :attr:`checkers`)."""
        out: list[CheckerGraphNode] = []
        for edge in self.checkers:
            if edge.target_node is None:
                continue
            out.append(cast(CheckerGraphNode, edge.target_node))
        return out

    def get_required_context_keys(self) -> frozenset[str]:
        """Return dot-path keys from :attr:`required_context` (``properties['key']`` per edge)."""
        out: set[str] = set()
        for edge in self.required_context:
            k = edge.properties.get("key")
            if isinstance(k, str):
                out.add(k)
        return frozenset(out)

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
    def _checker_nodes_for_aspect(aspect_callable: Callable[..., Any], _action_cls: type[Any]) -> list[CheckerGraphNode]:
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
                    aspect_callable=aspect_callable,
                    _action_cls=_action_cls,
                    checker_class=cc,
                    field_name=field,
                    required=bool(row.get("required", False)),
                    properties=extra if extra else None,
                ),
            )
        return nodes

    @staticmethod
    def _composition_edges_to_checkers(
        aspect_callable: Callable[..., Any],
        aspect_node_id: str,
        checker_nodes: list[CheckerGraphNode],
    ) -> list[CompositionGraphEdge]:
        return [
            CompositionGraphEdge(
                edge_name="@result_checker",
                is_dag=False,
                source_node_id=aspect_node_id,
                source_node_type=RegularAspectGraphNode.NODE_TYPE,
                target_node_id=ch.node_id,
                target_node_type=CheckerGraphNode.NODE_TYPE,
                target_node=ch,
            )
            for ch in checker_nodes
        ]

    @staticmethod
    def _required_context_nodes_for_aspect(
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
    ) -> list[RequiredContextGraphNode]:
        """One :class:`RequiredContextGraphNode` per ``@context_requires`` dot-path key (sorted)."""
        keys = ContextRequiresResolver.resolve_required_context_keys(aspect_callable)
        return [RequiredContextGraphNode(aspect_callable, _action_cls, k) for k in keys]

    @staticmethod
    def _composition_edges_to_required_context(
        _aspect_callable: Callable[..., Any],
        aspect_node_id: str,
        required_ctx: list[RequiredContextGraphNode],
    ) -> list[CompositionGraphEdge]:
        """``COMPOSITION`` edges: ``edge_name`` ``required_context``, dot-path key in ``properties['key']``."""
        return [
            CompositionGraphEdge(
                edge_name="required_context",
                is_dag=False,
                source_node_id=aspect_node_id,
                source_node_type=RegularAspectGraphNode.NODE_TYPE,
                target_node_id=rn.node_id,
                target_node_type=RequiredContextGraphNode.NODE_TYPE,
                target_node=rn,
                properties={"key": rn.node_obj.context_key},
            )
            for rn in required_ctx
        ]
