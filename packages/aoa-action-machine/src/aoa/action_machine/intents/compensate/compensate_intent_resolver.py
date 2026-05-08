# packages/aoa-action-machine/src/aoa/action_machine/intents/compensate/compensate_intent_resolver.py
"""CompensateIntentResolver — resolves compensator callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class CompensateIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve compensator intent declarations from one action class.
    CONTRACT: Returns own-class ``@compensate`` callables in declaration order and does not materialize graph nodes.
    FAILURES: :exc:`ValueError` from :meth:`resolve_description` or :meth:`resolve_target_aspect_name` when ``_compensate_meta`` is missing or not a ``dict``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_compensators(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@compensate`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: getattr(fn, "_compensate_meta", None) is not None,
        )

    @staticmethod
    def resolve_description(call_like: Any) -> Any:
        """Return ``@compensate`` ``description`` from scratch; raise when ``_compensate_meta`` is not a ``dict``."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        meta = getattr(func, "_compensate_meta", None)
        if not isinstance(meta, dict):
            raise ValueError(
                f"{TypeIntrospection.qualname_of(func)} has no usable @compensate description "
                "required for graph metadata resolution.",
            )
        return meta.get("description")

    @staticmethod
    def resolve_target_aspect_name(call_like: Any) -> str | None:
        """Return ``@compensate`` target_aspect_name from callable scratch when present."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        meta = getattr(func, "_compensate_meta", None)
        if not isinstance(meta, dict):
            raise ValueError(
                f"{TypeIntrospection.qualname_of(func)} has no usable @compensate target_aspect_name scratch "
                "required for graph metadata resolution.",
            )
        raw = meta.get("target_aspect_name")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None
