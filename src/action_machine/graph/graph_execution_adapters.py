# src/action_machine/graph/graph_execution_adapters.py
"""
Graph execution adapters: rehydrate tuple-based facet rows into typed snapshot records.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Convert serialized/hashable facet metadata rows (tuple pairs from graph node
``meta``) back into typed snapshot row objects used by runtime execution
components.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    graph node meta row (tuple[tuple[str, Any], ...])
                    │
                    ▼
              _row_dict(row)
                    │
                    ├─ aspect_row_to_aspect(...)
                    ├─ checker_row_to_checker(...)
                    ├─ compensator_row_to_compensator(...)
                    └─ on_error_row_to_error_handler(...)
                    │
                    ▼
        typed Snapshot row dataclasses for runtime consumers

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Input row shape is ``FacetMetaRow`` (hashable tuple pairs).
- Adapters normalize ``context_keys`` to ``frozenset``.
- Checker ``extra_params`` accepts dict or pair-iterable forms.
- Functions are pure row-mapping utilities and do not mutate coordinator state.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Missing required keys in a row raise ``KeyError``.
- Type mismatches propagate from constructor expectations/casts.
- This module assumes row contract compatibility with inspector payload emitters.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Runtime row-to-typed-record adapter layer for graph metadata.
CONTRACT: Reconstruct typed snapshot row objects from serialized facet metadata tuples.
INVARIANTS: Mapping is deterministic; no side effects; normalization of optional iterable fields.
FLOW: facet row tuple -> dict view -> typed snapshot row object.
FAILURES: Row shape/key/type mismatches raise standard Python mapping/type errors.
EXTENSION POINTS: Add adapters for new facet row types as inspector payloads evolve.
AI-CORE-END
"""

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
