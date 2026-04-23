# src/action_machine/introspection_tools/intent_introspection.py
"""
Intent-scratch introspection: recognize ActionMachine pipeline callables from class ``vars``,
read normalized ``description`` strings from decorator metadata by ``CallableKind``,
and read class-level ``@meta`` scratch (``_meta_info``) as a plain mapping.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any

from graph.base_intent_inspector import BaseIntentInspector


class CallableKind(StrEnum):
    """Own-class intent callables: ``@regular_aspect``, ``@summary_aspect``, ``@compensate``, ``@on_error``."""

    REGULAR_ASPECT = "regular_aspect"
    SUMMARY_ASPECT = "summary_aspect"
    COMPENSATE = "compensate"
    ON_ERROR = "on_error"


class IntentIntrospection:
    """Inspect class namespaces using intent decorator scratch (``_new_aspect_meta``, etc.)."""

    @staticmethod
    def meta_info_dict(host_cls: type) -> dict[str, Any]:
        """
        Return ``_meta_info`` written by ``@meta`` on ``host_cls``, or ``{}`` when absent or not a mapping.
        """
        raw = getattr(host_cls, "_meta_info", None)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def description_for_callable(call_like: Any, callable_kind: CallableKind | str) -> str | None:
        """
        Return strip-trimmed user ``description`` from intent scratch for ``callable_kind``, or ``None``.

        Unwraps ``property`` getters like :meth:`~graph.base_intent_inspector.BaseIntentInspector._unwrap_declaring_class_member`.
        """
        resolved_kind = CallableKind(callable_kind)
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        meta: Any
        match resolved_kind:
            case CallableKind.REGULAR_ASPECT:
                meta = getattr(func, "_new_aspect_meta", None)
                if not isinstance(meta, Mapping) or meta.get("type") != "regular":
                    return None
            case CallableKind.SUMMARY_ASPECT:
                meta = getattr(func, "_new_aspect_meta", None)
                if not isinstance(meta, Mapping) or meta.get("type") != "summary":
                    return None
            case CallableKind.COMPENSATE:
                meta = getattr(func, "_compensate_meta", None)
            case CallableKind.ON_ERROR:
                meta = getattr(func, "_on_error_meta", None)
        if not isinstance(meta, Mapping):
            return None
        raw = meta.get("description")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    @staticmethod
    def collect_own_class_callables_by_callable_kind(
        owner_class: type,
        callable_kind: CallableKind | str,
    ) -> list[Callable[..., Any]]:
        """Own-class callables in ``vars(owner_class)`` order whose scratch matches ``callable_kind`` (enum or string)."""
        resolved_kind = CallableKind(callable_kind)
        matching_callables: list[Callable[..., Any]] = []
        for _attr_name, namespace_entry in vars(owner_class).items():
            candidate = (
                namespace_entry.fget
                if isinstance(namespace_entry, property) and namespace_entry.fget is not None
                else namespace_entry
            )
            if not callable(candidate):
                continue
            match resolved_kind:
                case CallableKind.REGULAR_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "regular":
                        continue
                case CallableKind.SUMMARY_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "summary":
                        continue
                case CallableKind.COMPENSATE:
                    if getattr(candidate, "_compensate_meta", None) is None:
                        continue
                case CallableKind.ON_ERROR:
                    if getattr(candidate, "_on_error_meta", None) is None:
                        continue
            matching_callables.append(candidate)
        return matching_callables
