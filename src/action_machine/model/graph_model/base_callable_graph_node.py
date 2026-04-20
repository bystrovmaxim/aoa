# src/action_machine/model/graph_model/base_callable_graph_node.py
"""
BaseCallableGraphNode — abstract :class:`~graph.base_graph_node.BaseGraphNode` for action-hosted callables.

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

    unbound/bound method  ->  :meth:`_underlying_callable`
              |
              v
    ``__qualname__`` path under ``__module__``  ->  host ``type[BaseAction]``
    unwrapped ``__name__``  ->  method name for ``label`` / ``node_id`` fragments

    Own-class decorator scan: :meth:`get_decorated_callable` then
    :meth:`collect_own_class_callables_for_kind` with :class:`IntentCallableKind`.
"""

from __future__ import annotations

import inspect
import sys
from abc import ABC
from collections.abc import Callable
from enum import StrEnum
from types import MethodType
from typing import Any, cast

from action_machine.model.base_action import BaseAction
from graph.base_graph_node import BaseGraphNode


class IntentCallableKind(StrEnum):
    """
    Kind of intent-marked method to collect from a class's own namespace (``vars`` only, no MRO).

    Matches method-level scratch from ``@regular_aspect``, ``@summary_aspect``,
    ``@compensate``, and ``@on_error``.
    """

    REGULAR_ASPECT = "regular_aspect"
    SUMMARY_ASPECT = "summary_aspect"
    COMPENSATE = "compensate"
    ON_ERROR = "on_error"


class BaseCallableGraphNode(BaseGraphNode[Callable[..., Any]], ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract base for interchange nodes whose ``node_obj`` is a callable on a ``BaseAction`` host.
    CONTRACT: Subclasses supply concrete ``NODE_TYPE`` / ``node_id`` rules; host class and method name come from :meth:`resolve_host_action_class` and :meth:`resolve_method_name`.
    AI-CORE-END
    """

    @staticmethod
    def get_decorated_callable(namespace_entry: Any) -> Any:
        """
        From one ``vars(owner_class)`` value, return the object that carries method-level decorator metadata.

        For ``property``, that is ``fget`` when present; otherwise the namespace value is returned as-is.
        """
        if isinstance(namespace_entry, property) and namespace_entry.fget is not None:
            return namespace_entry.fget
        return namespace_entry

    @staticmethod
    def collect_own_class_callables_for_kind(
        owner_class: type,
        kind: IntentCallableKind | str,
    ) -> list[Callable[..., Any]]:
        """
        List callables declared directly on ``owner_class`` whose decorator metadata matches ``kind``.

        Order follows ``vars(owner_class)`` insertion order (no MRO walk).

        ``kind`` may be an :class:`IntentCallableKind` member or its string value
        (e.g. ``\"regular_aspect\"``).

        Aspects: ``_new_aspect_meta["type"]``; compensators: ``_compensate_meta``;
        error handlers: ``_on_error_meta``.
        """
        resolved_kind = IntentCallableKind(kind)
        matching_callables: list[Callable[..., Any]] = []
        for _attr_name, namespace_entry in vars(owner_class).items():
            candidate = BaseCallableGraphNode.get_decorated_callable(namespace_entry)
            if not callable(candidate):
                continue
            match resolved_kind:
                case IntentCallableKind.REGULAR_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "regular":
                        continue
                case IntentCallableKind.SUMMARY_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "summary":
                        continue
                case IntentCallableKind.COMPENSATE:
                    if getattr(candidate, "_compensate_meta", None) is None:
                        continue
                case IntentCallableKind.ON_ERROR:
                    if getattr(candidate, "_on_error_meta", None) is None:
                        continue
            matching_callables.append(candidate)
        return matching_callables

    @staticmethod
    def _underlying_callable(func: Callable[..., Any]) -> Callable[..., Any]:
        """Strip ``MethodType`` wrapper, then ``inspect.unwrap`` through decorator ``__wrapped__`` chains."""
        if isinstance(func, MethodType):
            func = func.__func__
        return cast(Callable[..., Any], inspect.unwrap(func))

    @staticmethod
    def resolve_method_name(func: Callable[..., Any]) -> str:
        """Python method name (``__name__``) of the underlying function."""
        return BaseCallableGraphNode._underlying_callable(func).__name__

    @staticmethod
    def resolve_host_action_class(func: Callable[..., Any]) -> type[BaseAction[Any, Any]]:
        """
        Resolve the owning ``BaseAction`` subclass from an unbound/bound aspect (or similar) callable.

        Uses :meth:`_underlying_callable` plus ``__qualname__`` / ``__module__`` (same idea for
        regular/summary aspects, ``@compensate``, ``@on_error``, and checker helpers
        that return the original ``func`` from decorators in this codebase).
        """
        raw = BaseCallableGraphNode._underlying_callable(func)
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
        for name_segment in parts[:-1]:
            try:
                obj = getattr(obj, name_segment)
            except AttributeError as exc:
                msg = (
                    f"Cannot resolve host action class: "
                    f"no attribute {name_segment!r} while walking {parts!r} from module {mod_name!r}"
                )
                raise TypeError(msg) from exc

        if not isinstance(obj, type):
            msg = f"Cannot resolve host action class: expected a type, got {type(obj).__name__}"
            raise TypeError(msg)

        if not issubclass(obj, BaseAction):
            msg = f"Cannot resolve host action class: {obj!r} is not a BaseAction subclass"
            raise TypeError(msg)

        return obj
