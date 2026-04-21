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
empty. Host class and method name come from :class:`TypeIntrospection`.

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

from action_machine.introspection_tools import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class ErrorHandlerGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for an ``@on_error`` callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``error_handler``; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "ErrorHandler"

    def __init__(self, handler_func: Callable[..., Any]) -> None:
        action_cls = TypeIntrospection.owner_type_for_method(handler_func)
        method_name = TypeIntrospection.unwrapped_callable_name(handler_func)
        action_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=ErrorHandlerGraphNode.NODE_TYPE,
            label=method_name,
            properties={},
            edges=[],
            node_obj=handler_func,
        )
