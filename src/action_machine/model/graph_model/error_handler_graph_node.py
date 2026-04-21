# src/action_machine/model/graph_model/error_handler_graph_node.py
"""
ErrorHandlerGraphNode — interchange node for an ``@on_error`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one error-handler
**callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``error_handler``, ``label`` is the method name, and ``properties`` / ``edges`` are
empty. Host class and name are resolved via :class:`BaseCallableGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Callable[..., Any]   unbound/bound ``@on_error`` method  ->  ``node_obj``
              │
              v
    ErrorHandlerGraphNode(handler_func)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.model.graph_model.base_callable_graph_node import BaseCallableGraphNode
from action_machine.tools import Introspection


@dataclass(init=False, frozen=True)
class ErrorHandlerGraphNode(BaseCallableGraphNode):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for an ``@on_error`` callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``Introspection.full_qualname(action_cls) + ':' + method_name`` from :class:`BaseCallableGraphNode` resolvers; :attr:`NODE_TYPE` matches facet ``error_handler``; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "error_handler"

    def __init__(self, handler_func: Callable[..., Any]) -> None:
        action_cls = BaseCallableGraphNode.resolve_host_action_class(handler_func)
        method_name = BaseCallableGraphNode.resolve_method_name(handler_func)
        action_id = Introspection.full_qualname(action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=ErrorHandlerGraphNode.NODE_TYPE,
            label=method_name,
            properties={},
            edges=[],
            node_obj=handler_func,
        )
