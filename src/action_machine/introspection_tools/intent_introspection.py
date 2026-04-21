# src/action_machine/introspection_tools/intent_introspection.py
"""
Intent-scratch introspection: recognize ActionMachine pipeline callables from class ``vars``.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any


class CallableKind(StrEnum):
    """Own-class intent callables: ``@regular_aspect``, ``@summary_aspect``, ``@compensate``, ``@on_error``."""

    REGULAR_ASPECT = "regular_aspect"
    SUMMARY_ASPECT = "summary_aspect"
    COMPENSATE = "compensate"
    ON_ERROR = "on_error"


class IntentIntrospection:
    """Inspect class namespaces using intent decorator scratch (``_new_aspect_meta``, etc.)."""

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
