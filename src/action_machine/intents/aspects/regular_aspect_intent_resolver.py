# src/action_machine/intents/aspects/regular_aspect_intent_resolver.py
"""RegularAspectIntentResolver — resolves regular aspect callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_intent_inspector import BaseIntentInspector


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
    FAILURES: :exc:`ValueError` from :meth:`resolve_description` when scratch is not a regular-aspect callable or carries no non-empty ``description``.
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
    def resolve_description(call_like: Any) -> str:
        """Return stripped ``@regular_aspect`` description or raise :exc:`ValueError`."""
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        if not callable(func):
            raise ValueError(
                "Expected an aspect callable or property exposing one; "
                f"got {type(call_like).__name__}: {call_like!r}.",
            )
        meta = getattr(func, "_new_aspect_meta", None)
        if not isinstance(meta, dict) or meta.get("type") != "regular":
            raise ValueError(_missing_regular_aspect_description_message(func))
        desc = TypeIntrospection.description_from_meta(meta)
        if desc is None:
            raise ValueError(_missing_regular_aspect_description_message(func))
        return desc
