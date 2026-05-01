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
``edges`` are empty. Host class and method name come from :class:`TypeIntrospection`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.intents.aspects.summary_aspect_intent_resolver import SummaryAspectIntentResolver
from action_machine.intents.context_requires.context_requires_resolver import ContextRequiresResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class SummaryAspectGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a summary aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``SummaryAspect``; ``properties`` include ``description`` from :meth:`~action_machine.intents.aspects.summary_aspect_intent_resolver.SummaryAspectIntentResolver.resolve_description`; ``edges`` empty.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "SummaryAspect"

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

    def get_required_context_keys(self) -> frozenset[str]:
        """Declare ``@context_requires`` keys via resolver (same behaviour as runtime)."""
        return frozenset(ContextRequiresResolver.resolve_required_context_keys(self.node_obj))
