# src/action_machine/graph/graph_execution_adapters.py
"""Rehydrate graph facet rows (tuple of str/Any pairs) into snapshot field types."""

from __future__ import annotations

from typing import Any, cast

from action_machine.graph.inspectors.aspect_intent_inspector import AspectIntentInspector
from action_machine.graph.inspectors.checker_intent_inspector import CheckerIntentInspector
from action_machine.graph.inspectors.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.graph.inspectors.on_error_intent_inspector import OnErrorIntentInspector

# One facet row in ``meta["aspects"]`` / ``meta["checkers"]`` / … — hashable pairs.
FacetMetaRow = tuple[tuple[str, Any], ...]


def _row_dict(row: FacetMetaRow) -> dict[str, Any]:
    return dict(row)


def aspect_row_to_aspect(row: FacetMetaRow) -> AspectIntentInspector.Snapshot.Aspect:
    d = _row_dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    return AspectIntentInspector.Snapshot.Aspect(
        method_name=d["method_name"],
        aspect_type=d["aspect_type"],
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )


def checker_row_to_checker(row: FacetMetaRow) -> CheckerIntentInspector.Snapshot.Checker:
    d = _row_dict(row)
    extra = d["extra_params"]
    if isinstance(extra, dict):
        ep = extra
    else:
        ep = dict(extra)
    return CheckerIntentInspector.Snapshot.Checker(
        method_name=d["method_name"],
        checker_class=d["checker_class"],
        field_name=d["field_name"],
        required=bool(d["required"]),
        extra_params=ep,
    )


def compensator_row_to_compensator(
    row: FacetMetaRow,
) -> CompensateIntentInspector.Snapshot.Compensator:
    d = _row_dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    return CompensateIntentInspector.Snapshot.Compensator(
        method_name=d["method_name"],
        target_aspect_name=d["target_aspect_name"],
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )


def on_error_row_to_error_handler(
    row: FacetMetaRow,
) -> OnErrorIntentInspector.Snapshot.ErrorHandler:
    d = _row_dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    et = d["exception_types"]
    return OnErrorIntentInspector.Snapshot.ErrorHandler(
        method_name=d["method_name"],
        exception_types=cast("tuple[type[Exception], ...]", tuple(et)),
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )
