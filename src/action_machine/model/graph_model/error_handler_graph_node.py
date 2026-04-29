# src/action_machine/model/graph_model/error_handler_graph_node.py
"""
ErrorHandlerGraphNode — interchange node for an ``@on_error`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one error-handler
**callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``error_handler``, ``label`` is the method name; ``properties`` may carry
``description`` and ``exception_types`` from ``OnErrorIntentResolver`` when present;
``edges`` are empty. Host class and method name come from :class:`TypeIntrospection`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.intents.on_error.on_error_intent_resolver import OnErrorIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class ErrorHandlerGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for an ``@on_error`` callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``error_handler``; ``properties`` include ``description`` and ``exception_types`` when resolver methods return them; ``edges`` empty.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "ErrorHandler"

    def __init__(self, handler_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        method_name = TypeIntrospection.unwrapped_callable_name(handler_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        desc = OnErrorIntentResolver.resolve_description(handler_func)
        exception_types = OnErrorIntentResolver.resolve_exception_types(handler_func)
        properties: dict[str, Any] = {}
        if desc is not None:
            properties["description"] = desc
        if exception_types:
            properties["exception_types"] = exception_types
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=ErrorHandlerGraphNode.NODE_TYPE,
            label=method_name,
            properties=properties,
            node_obj=handler_func,
        )
