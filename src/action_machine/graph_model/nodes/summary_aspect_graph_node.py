# src/action_machine/graph_model/nodes/summary_aspect_graph_node.py
"""
SummaryAspectGraphNode — interchange node for a ``@summary_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one summary
aspect **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``SummaryAspect``, ``label`` is the method name; ``properties`` include ``description`` from
``SummaryAspectIntentResolver.resolve_description`` or that call raises if ``@summary_aspect`` metadata or description is unusable;
``@context_requires`` wired as :attr:`required_context` composition edges (:class:`~action_machine.graph_model.edges.required_context_graph_edge.RequiredContextGraphEdge`).
Host class and method name come from :class:`TypeIntrospection`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.intents.aspects.summary_aspect_intent_resolver import SummaryAspectIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

from ..edges.required_context_graph_edge import RequiredContextGraphEdge


@dataclass(init=False, frozen=True)
class SummaryAspectGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a summary aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``SummaryAspect``; ``properties`` include ``description`` from :meth:`~action_machine.intents.aspects.summary_aspect_intent_resolver.SummaryAspectIntentResolver.resolve_description`; :attr:`required_context` via :meth:`~action_machine.graph_model.edges.required_context_graph_edge.RequiredContextGraphEdge.get_required_context_edges`; companions are wired ``RequiredContextGraphNode`` targets on those edges.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "SummaryAspect"
    required_context: list[RequiredContextGraphEdge]

    def __init__(self, summary_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        method_name = TypeIntrospection.unwrapped_callable_name(summary_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=SummaryAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": SummaryAspectIntentResolver.resolve_description(summary_func)},
            node_obj=summary_func,
        )
        object.__setattr__(self, "required_context", RequiredContextGraphEdge.get_required_context_edges(summary_func, _action_cls, self))

    def get_required_context_keys(self) -> frozenset[str]:
        """Return dot-path keys from :attr:`required_context` (``properties['key']`` per edge)."""
        out: set[str] = set()
        for edge in self.required_context:
            k = edge.properties.get("key")
            if isinstance(k, str):
                out.add(k)
        return frozenset(out)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return required-context composition edges materialized on this node."""
        return [*self.required_context]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return required-context companion nodes referenced by composition edges."""
        ctx = [edge.target_node for edge in self.required_context if edge.target_node is not None]
        return [*ctx]
