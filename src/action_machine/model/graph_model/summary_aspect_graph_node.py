# src/action_machine/model/graph_model/summary_aspect_graph_node.py
"""
SummaryAspectGraphNode — interchange node for a ``@summary_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one summary
aspect **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``SummaryAspect``, ``label`` is the method name, and ``properties`` / ``edges`` are
empty. Host class and name are resolved via :class:`BaseCallableGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Callable[..., Any]   unbound/bound aspect method  ->  ``node_obj``
              │
              v
    SummaryAspectGraphNode(aspect_func)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.model.graph_model.base_callable_graph_node import BaseCallableGraphNode
from action_machine.tools import Introspection


@dataclass(init=False, frozen=True)
class SummaryAspectGraphNode(BaseCallableGraphNode):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a summary aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``Introspection.full_qualname(action_cls) + ':' + method_name`` from :class:`BaseCallableGraphNode` resolvers; :attr:`NODE_TYPE` matches facet ``SummaryAspect``; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "SummaryAspect"

    def __init__(self, aspect_func: Callable[..., Any]) -> None:
        action_cls = Introspection.owner_type_for_method(aspect_func)
        method_name = Introspection.unwrapped_callable_name(aspect_func)
        action_id = Introspection.full_qualname(action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=SummaryAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={},
            edges=[],
            node_obj=aspect_func,
        )
