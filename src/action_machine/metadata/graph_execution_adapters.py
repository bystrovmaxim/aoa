# src/action_machine/metadata/graph_execution_adapters.py
"""Convert graph facet tuples (node_meta) into runtime dataclasses used by the machine."""

from __future__ import annotations

from typing import Any, cast

from action_machine.aspects.aspect_intent_inspector import AspectIntentInspector
from action_machine.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.compensate.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.on_error.on_error_intent_inspector import OnErrorIntentInspector


def aspect_tuple_to_meta(
    row: tuple[Any, ...],
) -> AspectIntentInspector.Snapshot.Aspect:
    aspect_type, method_name, description, method_ref, context_keys = row
    ck = context_keys if isinstance(context_keys, frozenset) else frozenset(context_keys or ())
    return AspectIntentInspector.Snapshot.Aspect(
        method_name=method_name,
        aspect_type=aspect_type,
        description=description,
        method_ref=method_ref,
        context_keys=ck,
    )


def checker_tuple_to_meta(
    row: tuple[Any, ...],
) -> CheckerIntentInspector.Snapshot.Checker:
    method_name, checker_class, field_name, required, extra_kv = row
    return CheckerIntentInspector.Snapshot.Checker(
        method_name=method_name,
        checker_class=checker_class,
        field_name=field_name,
        required=bool(required),
        extra_params=dict(extra_kv),
    )


def compensator_tuple_to_meta(
    row: tuple[Any, ...],
) -> CompensateIntentInspector.Snapshot.Compensator:
    method_name, target_aspect_name, description, method_ref, context_keys = row
    ck = context_keys if isinstance(context_keys, frozenset) else frozenset(context_keys or ())
    return CompensateIntentInspector.Snapshot.Compensator(
        method_name=method_name,
        target_aspect_name=target_aspect_name,
        description=description,
        method_ref=method_ref,
        context_keys=ck,
    )


def on_error_tuple_to_meta(
    row: tuple[Any, ...],
) -> OnErrorIntentInspector.Snapshot.ErrorHandler:
    method_name, exception_types, description, method_ref, context_keys = row
    ck = context_keys if isinstance(context_keys, frozenset) else frozenset(context_keys or ())
    et = tuple(exception_types)
    return OnErrorIntentInspector.Snapshot.ErrorHandler(
        method_name=method_name,
        exception_types=cast("tuple[type[Exception], ...]", et),
        description=description,
        method_ref=method_ref,
        context_keys=ck,
    )
