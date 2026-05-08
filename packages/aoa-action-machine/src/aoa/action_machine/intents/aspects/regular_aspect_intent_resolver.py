# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/regular_aspect_intent_resolver.py
"""RegularAspectIntentResolver — resolves regular aspect callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def _missing_regular_aspect_description_message(func: Callable[..., Any]) -> str:
    qual = TypeIntrospection.qualname_of(func)
    return (
        f"{qual} has no usable @regular_aspect description "
        "required for graph metadata resolution."
    )


class RegularAspectIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve regular aspect intent declarations from one action class.
    CONTRACT: Returns own-class ``@regular_aspect`` callables in declaration order and does not materialize graph nodes.
    FAILURES: :exc:`ValueError` from :meth:`resolve_description` when the callable is not an aspect target, or ``_new_aspect_meta`` is missing or not a ``dict``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_regular_aspects(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@regular_aspect`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: (
                isinstance(meta := getattr(fn, "_new_aspect_meta", None), dict)
                and meta.get("type") == "regular"
            ),
        )

    @staticmethod
    def resolve_description(call_like: Any) -> Any:
        """Return ``@regular_aspect`` ``description`` from scratch (exact ``dict`` value); raise when scratch is absent."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        if not callable(func):
            raise ValueError(
                "Expected an aspect callable or property exposing one; "
                f"got {type(call_like).__name__}: {call_like!r}.",
            )
        meta = getattr(func, "_new_aspect_meta", None)
        if not isinstance(meta, dict):
            raise ValueError(_missing_regular_aspect_description_message(func))
        return meta.get("description")
