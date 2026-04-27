# src/action_machine/introspection_tools/intent_introspection.py
"""
Intent-scratch introspection: read class-level ``@meta`` scratch and callable
``description`` strings from decorator metadata.
"""

from __future__ import annotations

from collections.abc import Mapping
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
