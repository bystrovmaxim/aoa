# src/action_machine/model/graph_model/base_callable_graph_node.py
"""
BaseCallableGraphNode — abstract :class:`~graph.base_graph_node.BaseGraphNode` for action-hosted callables.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Shared interchange plumbing for pipeline callables attached to a ``BaseAction``
subclass (regular/summary aspects, compensators, ``@on_error`` handlers, …):
``node_obj`` is always the **callable**; the host action class comes from
:meth:`Introspection.owner_type_for_method`, and the Python method name from
:meth:`Introspection.unwrapped_callable_name`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    :meth:`Introspection.owner_type_for_method`  ->  host class
    :meth:`Introspection.unwrapped_callable_name`  ->  method name for ``label`` / ``node_id`` fragments

    Own-class decorator scan: :meth:`get_decorated_callable` then
    :meth:`collect_own_class_callables_for_kind` with :class:`IntentCallableKind`.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from enum import StrEnum
from typing import Any

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
    CONTRACT: Subclasses supply concrete ``NODE_TYPE`` / ``node_id`` rules; host class via :meth:`Introspection.owner_type_for_method`, method name from :meth:`Introspection.unwrapped_callable_name`.
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
