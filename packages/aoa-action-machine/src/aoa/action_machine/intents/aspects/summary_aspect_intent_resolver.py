# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/summary_aspect_intent_resolver.py
"""SummaryAspectIntentResolver — resolves summary aspect callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.duplicate_summary_aspect_error import DuplicateSummaryAspectError
from aoa.action_machine.exceptions.intent_resolution_error import IntentResolutionError
from aoa.action_machine.exceptions.missing_declaration_error import MissingDeclarationError
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def _missing_summary_aspect_description_message(func: Callable[..., Any]) -> str:
    qual = TypeIntrospection.qualname_of(func)
    return f"{qual} has no usable @summary_aspect description " "required for graph metadata resolution."


class SummaryAspectIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve summary aspect intent declarations from one action class.
    CONTRACT: :meth:`resolve_summary_aspects` returns the own-class ``@summary_aspect`` callables in declaration order and does not materialize graph nodes; an operation with two of them raises :exc:`~aoa.action_machine.exceptions.DuplicateSummaryAspectError`, because an operation answers once.
    FAILURES: :exc:`DuplicateSummaryAspectError` from :meth:`resolve_summary_aspects` when the operation declares more than one exit point. :exc:`ValueError` from :meth:`resolve_description` when the callable is not an aspect target, or ``_new_aspect_meta`` is missing or not a ``dict``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_summary_aspects(action_cls: type) -> list[Callable[..., Any]]:
        """
        Return the own-class ``@summary_aspect`` callables, or refuse a second one.

        Raises:
            DuplicateSummaryAspectError: the operation declares more than one exit point.
        """
        declared = TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: (
                isinstance(meta := getattr(fn, "_new_aspect_meta", None), dict) and meta.get("type") == "summary"
            ),
        )
        if len(declared) > 1:
            names = ", ".join(sorted(method.__name__ for method in declared))
            raise DuplicateSummaryAspectError(
                f"{action_cls.__name__} declares more than one exit point ({names}); an operation answers once."
            )
        return declared

    @staticmethod
    def resolve_description(call_like: Any) -> Any:
        """Return ``@summary_aspect`` ``description`` from scratch (exact ``dict`` value); raise when scratch is absent."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        if not callable(func):
            raise IntentResolutionError(
                "Expected an aspect callable or property exposing one; "
                f"got {type(call_like).__name__}: {call_like!r}.",
            )
        meta = getattr(func, "_new_aspect_meta", None)
        if not isinstance(meta, dict):
            raise MissingDeclarationError(_missing_summary_aspect_description_message(func))
        return meta.get("description")
