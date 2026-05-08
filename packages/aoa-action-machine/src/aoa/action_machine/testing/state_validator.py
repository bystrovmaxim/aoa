# packages/aoa-action-machine/src/aoa/action_machine/testing/state_validator.py
"""
State validation using aspect checkers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When testing a single aspect (``run_aspect``) or summary aspect
(``run_summary``), state is provided manually by test code. This state must
contain required fields that preceding regular aspects would produce in a full
pipeline run.

This module validates state BEFORE aspect execution, surfacing test setup
errors early with informative diagnostics.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

[aspects metadata + checker callback]
                |
                v
   validate_state_for_aspect / validate_state_for_summary
                |
                v
   select relevant regular aspects (preceding or all)
                |
                v
   required field presence check in state
                |
                v
      checker_class(...).check(state)
                |
                v
     StateValidationError on first mismatch

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS:
- Validation order follows declared regular-aspect order.
- Missing required fields fail before type/constraint checks.
- Error payload carries ``field`` and ``source_aspect`` when available.

"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


class StateValidationError(Exception):
    """
    Validation error for state passed into isolated aspect execution.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        source_aspect: str | None = None,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.source_aspect = source_aspect


def _find_aspect_index(aspects: Sequence[Any], aspect_name: str) -> int:
    """
    Find aspect index by method name in declared aspect list.
    """
    for i, aspect in enumerate(aspects):
        if aspect.method_name == aspect_name:
            return i

    available = [a.method_name for a in aspects]
    raise StateValidationError(
        f"Aspect '{aspect_name}' was not found in metadata. "
        f"Available aspects: {available}."
    )


def _get_preceding_regular_checkers(
    aspects: Sequence[Any],
    get_checkers_for_aspect: Callable[[str], tuple[Any, ...]],
    up_to_index: int,
) -> list[tuple[str, Any]]:
    """
    Collect checkers for regular aspects before ``up_to_index`` (exclusive).
    """
    result: list[tuple[str, Any]] = []

    for i in range(up_to_index):
        aspect = aspects[i]
        if aspect.aspect_type != "regular":
            continue
        checkers = get_checkers_for_aspect(aspect.method_name)
        for checker_meta in checkers:
            result.append((aspect.method_name, checker_meta))

    return result


def _get_all_regular_checkers(
    aspects: Sequence[Any],
    get_checkers_for_aspect: Callable[[str], tuple[Any, ...]],
) -> list[tuple[str, Any]]:
    """
    Collect checkers for all regular aspects.
    """
    result: list[tuple[str, Any]] = []

    for aspect in aspects:
        if aspect.aspect_type != "regular":
            continue
        checkers = get_checkers_for_aspect(aspect.method_name)
        for checker_meta in checkers:
            result.append((aspect.method_name, checker_meta))

    return result


def _validate_checker_against_state(
    checker_meta: Any,
    source_aspect: str,
    target_context: str,
    state: dict[str, Any],
) -> None:
    """
    Validate one state field against one checker metadata record.
    """
    field_name = checker_meta.field_name
    checker_class_name = checker_meta.checker_class.__name__
    required_label = "required" if checker_meta.required else "optional"

    # Validate required field presence.
    if checker_meta.required and field_name not in state:
        raise StateValidationError(
            f"{target_context} expects field '{field_name}' "
            f"({checker_class_name}, {required_label}) from aspect "
            f"'{source_aspect}', but it is missing in state.",
            field=field_name,
            source_aspect=source_aspect,
        )

    # Skip absent optional field.
    if field_name not in state:
        return

    # Validate value with checker instance.
    try:
        checker_instance = checker_meta.checker_class(
            checker_meta.field_name,
            required=checker_meta.required,
            **checker_meta.extra_params,
        )
        checker_instance.check(state)
    except Exception as exc:
        raise StateValidationError(
            f"{target_context} expects field '{field_name}' "
            f"({checker_class_name}, {required_label}) from aspect "
            f"'{source_aspect}': {exc}",
            field=field_name,
            source_aspect=source_aspect,
        ) from exc


def validate_state_for_aspect(
    aspects: Sequence[Any],
    get_checkers_for_aspect: Callable[[str], tuple[Any, ...]],
    aspect_name: str,
    state: dict[str, Any],
) -> None:
    """
    Validate state before running a specific aspect.
    """
    target_index = _find_aspect_index(aspects, aspect_name)
    preceding_checkers = _get_preceding_regular_checkers(
        aspects, get_checkers_for_aspect, target_index,
    )
    target_context = f"Aspect '{aspect_name}'"

    for source_aspect, checker_meta in preceding_checkers:
        _validate_checker_against_state(
            checker_meta, source_aspect, target_context, state,
        )


def validate_state_for_summary(
    aspects: Sequence[Any],
    get_checkers_for_aspect: Callable[[str], tuple[Any, ...]],
    state: dict[str, Any],
) -> None:
    """
    Validate state before running summary aspect.
    """
    all_checkers = _get_all_regular_checkers(aspects, get_checkers_for_aspect)

    for source_aspect, checker_meta in all_checkers:
        _validate_checker_against_state(
            checker_meta, source_aspect, "Summary", state,
        )
