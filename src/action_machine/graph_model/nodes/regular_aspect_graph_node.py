# src/action_machine/graph_model/nodes/regular_aspect_graph_node.py
"""
RegularAspectGraphNode — interchange node for a ``@regular_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One frozen vertex per ``@regular_aspect`` method on a ``BaseAction`` subclass:
``node_id`` is ``<action dotted qualname>:<method name>``; ``label`` is the method name;
``properties['description']`` comes from
:meth:`~action_machine.intents.aspects.regular_aspect_intent_resolver.RegularAspectIntentResolver.resolve_description`
(or that call raises on bad metadata).
Builds checker and ``@context_requires`` companions and composition edges ``@result_checker`` /
``@required_context`` (context key in ``properties['key']``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, cast

from action_machine.intents.aspects.regular_aspect_intent_resolver import RegularAspectIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

from ..edges.checker_graph_edge import CheckerGraphEdge
from ..edges.required_context_graph_edge import RequiredContextGraphEdge
from .checker_graph_node import CheckerGraphNode


@dataclass(init=False, frozen=True)
class RegularAspectGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a regular aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``RegularAspect``; ``properties`` include ``description`` from :meth:`~action_machine.intents.aspects.regular_aspect_intent_resolver.RegularAspectIntentResolver.resolve_description`; :attr:`checkers` (:class:`~action_machine.graph_model.edges.checker_graph_edge.CheckerGraphEdge` list) built via :meth:`~action_machine.graph_model.edges.checker_graph_edge.CheckerGraphEdge.get_checker_edges`; :attr:`required_context` via :meth:`~action_machine.graph_model.edges.required_context_graph_edge.RequiredContextGraphEdge.get_required_context_edges`; companion ``CheckerGraphNode`` / ``RequiredContextGraphNode`` rows from ``_checker_meta`` and ``@context_requires``. :meth:`get_required_context_keys` aggregates ``properties['key']``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "RegularAspect"
    checkers: list[CheckerGraphEdge]
    required_context: list[RequiredContextGraphEdge]

    def __init__(self, aspect_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        method_name = TypeIntrospection.unwrapped_callable_name(aspect_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        node_id = f"{action_id}:{method_name}"
        super().__init__(
            node_id=node_id,
            node_type=RegularAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": RegularAspectIntentResolver.resolve_description(aspect_func)},
            node_obj=aspect_func,
        )
        object.__setattr__(self, "checkers", CheckerGraphEdge.get_checker_edges(aspect_func, _action_cls, self))
        object.__setattr__(self, "required_context", RequiredContextGraphEdge.get_required_context_edges(aspect_func, _action_cls, self))

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
