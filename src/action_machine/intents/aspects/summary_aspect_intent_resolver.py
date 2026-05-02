# src/action_machine/intents/aspects/summary_aspect_intent_resolver.py
"""SummaryAspectIntentResolver — resolves summary aspect callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.system_core import TypeIntrospection


def _missing_summary_aspect_description_message(func: Callable[..., Any]) -> str:
    qual = TypeIntrospection.qualname_of(func)
    return (
        f"{qual} has no usable @summary_aspect description "
        "required for graph metadata resolution."
    )


class SummaryAspectIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve summary aspect intent declarations from one action class.
    CONTRACT: Returns own-class ``@summary_aspect`` callables in declaration order and does not materialize graph nodes.
    FAILURES: :exc:`ValueError` from :meth:`resolve_description` when scratch is not a summary-aspect callable or carries no non-empty ``description``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_summary_aspects(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@summary_aspect`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: (
                isinstance(meta := getattr(fn, "_new_aspect_meta", None), dict)
                and meta.get("type") == "summary"
            ),
        )

    @staticmethod
    def resolve_description(call_like: Any) -> str:
        """Return stripped ``@summary_aspect`` description or raise :exc:`ValueError`."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        if not callable(func):
            raise ValueError(
                "Expected an aspect callable or property exposing one; "
                f"got {type(call_like).__name__}: {call_like!r}.",
            )
        meta = getattr(func, "_new_aspect_meta", None)
        if not isinstance(meta, dict) or meta.get("type") != "summary":
            raise ValueError(_missing_summary_aspect_description_message(func))
        desc = TypeIntrospection.description_from_meta(meta)
        if desc is None:
            raise ValueError(_missing_summary_aspect_description_message(func))
        return desc
