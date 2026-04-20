# src/action_machine/model/graph_model/regular_aspect_graph_node.py
"""
RegularAspectGraphNode — interchange node for a ``@regular_aspect`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one regular
aspect **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``RegularAspect``, ``label`` is the method name, and ``properties`` / ``edges`` are
empty. Host class and name are resolved via :class:`CallableGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Callable[..., Any]   unbound/bound aspect method  ->  ``node_obj``
              │
              v
    RegularAspectGraphNode(aspect_func)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.model.graph_model.callable_graph_node import CallableGraphNode
from graph.qualified_name import cls_qualified_dotted_id


@dataclass(init=False, frozen=True)
class RegularAspectGraphNode(CallableGraphNode):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a regular aspect callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``cls_qualified_dotted_id(action_cls) + ':' + method_name`` from :class:`CallableGraphNode` resolvers; :attr:`NODE_TYPE` matches facet ``RegularAspect``; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "RegularAspect"

    def __init__(self, aspect_func: Callable[..., Any]) -> None:
        action_cls = CallableGraphNode.resolve_host_action_class(aspect_func)
        method_name = CallableGraphNode.resolve_method_name(aspect_func)
        action_id = cls_qualified_dotted_id(action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=RegularAspectGraphNode.NODE_TYPE,
            label=method_name,
            properties={},
            edges=[],
            node_obj=aspect_func,
        )
