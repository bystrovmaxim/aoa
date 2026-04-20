# src/action_machine/model/graph_model/callable_graph_node.py
"""
CallableGraphNode — abstract :class:`~graph.base_graph_node.BaseGraphNode` for action-hosted callables.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Shared interchange plumbing for pipeline callables attached to a ``BaseAction``
subclass (regular/summary aspects, compensators, ``@on_error`` handlers, …):
``node_obj`` is always the **callable**, while the host action class and Python
method name are recovered with :meth:`resolve_host_action_class` and
:meth:`resolve_method_name`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    unbound/bound method  ->  :meth:`_unwrap_to_function`
              |
              v
    ``__qualname__`` path under ``__module__``  ->  host ``type[BaseAction]``
    unwrapped ``__name__``  ->  method name for ``label`` / ``node_id`` fragments
"""

from __future__ import annotations

import inspect
import sys
from abc import ABC
from collections.abc import Callable
from types import MethodType
from typing import Any

from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode


class CallableGraphNode(BaseGraphNode[Callable[..., Any]], ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract base for interchange nodes whose ``node_obj`` is a callable on a ``BaseAction`` host.
    CONTRACT: Subclasses supply concrete ``NODE_TYPE`` / ``node_id`` rules; host class and method name come from :meth:`resolve_host_action_class` and :meth:`resolve_method_name`.
    AI-CORE-END
    """

    @staticmethod
    def _unwrap_to_function(func: Callable[..., Any]) -> Callable[..., Any]:
        """Strip ``MethodType`` wrapper and decorator ``__wrapped__`` chains."""
        if isinstance(func, MethodType):
            func = func.__func__
        return inspect.unwrap(func)

    @staticmethod
    def resolve_method_name(func: Callable[..., Any]) -> str:
        """Python method name (``__name__``) of the underlying function."""
        return CallableGraphNode._unwrap_to_function(func).__name__

    @staticmethod
    def resolve_host_action_class(func: Callable[..., Any]) -> type[BaseAction[Any, Any]]:
        """
        Resolve the owning ``BaseAction`` subclass from an unbound/bound aspect (or similar) callable.

        Uses ``inspect.unwrap`` plus ``__qualname__`` / ``__module__`` (same idea for
        regular/summary aspects, ``@compensate``, ``@on_error``, and checker helpers
        that return the original ``func`` from decorators in this codebase).
        """
        raw = CallableGraphNode._unwrap_to_function(func)
        qual = getattr(raw, "__qualname__", "") or ""
        parts = qual.split(".")
        if len(parts) < 2:
            msg = (
                "Cannot resolve host action class: expected a method "
                f"(``__qualname__`` like 'MyAction.method'), got {qual!r}"
            )
            raise TypeError(msg)

        mod_name = getattr(raw, "__module__", None)
        if not mod_name:
            msg = "Cannot resolve host action class: callable has no __module__"
            raise TypeError(msg)

        mod = sys.modules.get(mod_name)
        if mod is None:
            msg = f"Cannot resolve host action class: module {mod_name!r} is not loaded"
            raise TypeError(msg)

        obj: Any = mod
        for attr in parts[:-1]:
            try:
                obj = getattr(obj, attr)
            except AttributeError as exc:
                msg = (
                    f"Cannot resolve host action class: "
                    f"no attribute {attr!r} while walking {parts!r} from module {mod_name!r}"
                )
                raise TypeError(msg) from exc

        if not isinstance(obj, type):
            msg = f"Cannot resolve host action class: expected a type, got {type(obj).__name__}"
            raise TypeError(msg)

        if not issubclass(obj, BaseAction):
            msg = f"Cannot resolve host action class: {obj!r} is not a BaseAction subclass"
            raise TypeError(msg)

        return obj
