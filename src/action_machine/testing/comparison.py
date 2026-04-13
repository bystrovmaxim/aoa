# src/action_machine/testing/comparison.py
"""
Compare action execution results across machines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When TestBench executes an action on multiple machines (async and sync),
results must match. This module provides ``compare_results()``, which compares
two values and raises an informative exception describing concrete mismatches.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

[TestBench async result]      [TestBench sync result]
            |                           |
            +-----------compare_results-+
                            |
            +---------------+-------------------+
            |                                   |
    same type? no                        same type? yes
            |                                   |
  raise type mismatch                 BaseModel on both sides?
            |                                   |
            |                          +--------+--------+
            |                          |                 |
            |                         yes               no
            |                          |                 |
            |                model_dump + field diff     == fallback
            |                          |                 |
            +-------------> ResultMismatchError on any mismatch

INVARIANTS:
- Type mismatch is always checked before value comparison.
- BaseModel values are compared by ``model_dump()`` output, not object identity.
- Missing dict keys are represented as ``"<missing>"`` in difference payloads.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``ResultMismatchError`` is raised when compared results do not match.
- ``differences`` is populated for dict-level BaseModel mismatches and empty for
  type mismatch / plain ``==`` mismatch branches.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing.comparison import compare_results

    # Matching results -> no exception
    compare_results(result_async, "AsyncMachine", result_sync, "SyncMachine")

    # Mismatching results -> ResultMismatchError:
    # "Machine results diverged:
    #   AsyncMachine.order_id='ORD-1' vs SyncMachine.order_id='ORD-2'
    #   AsyncMachine.total=1500.0 vs SyncMachine.total=999.0"

═══════════════════════════════════════════════════════════════════════════════
AI-CORE
═══════════════════════════════════════════════════════════════════════════════

Use this module in tests to enforce runtime parity between async and sync
machines and get deterministic, field-level mismatch diagnostics.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ResultMismatchError(AssertionError):
    """
    Results from two machines do not match.

    Subclass of ``AssertionError`` so pytest shows parity failures as assertion
    failures with full traceback and message.
    """

    def __init__(
        self,
        message: str,
        left_name: str,
        right_name: str,
        differences: list[tuple[str, Any, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.left_name = left_name
        self.right_name = right_name
        self.differences = differences or []


def _find_dict_differences(
    left_dict: dict[str, Any],
    right_dict: dict[str, Any],
    left_name: str,
    right_name: str,
) -> list[tuple[str, Any, Any]]:
    """
    Find field-level mismatches between two dictionaries.
    """
    all_keys = sorted(set(left_dict.keys()) | set(right_dict.keys()))
    differences: list[tuple[str, Any, Any]] = []

    _missing = "<missing>"

    for key in all_keys:
        left_val = left_dict.get(key, _missing)
        right_val = right_dict.get(key, _missing)
        if left_val != right_val:
            differences.append((key, left_val, right_val))

    return differences


def _format_differences(
    differences: list[tuple[str, Any, Any]],
    left_name: str,
    right_name: str,
) -> str:
    """
    Format mismatch list into a readable multi-line string.
    """
    lines: list[str] = []
    for field, left_val, right_val in differences:
        lines.append(
            f"  {left_name}.{field}={left_val!r} vs "
            f"{right_name}.{field}={right_val!r}"
        )
    return "\n".join(lines)


def compare_results(
    left: Any,
    left_name: str,
    right: Any,
    right_name: str,
) -> None:
    """
    Compare results from two machines and raise on divergence.
    """
    # Type must match before value-level comparison.
    if type(left) is not type(right):
        raise ResultMismatchError(
            f"Result types differ: {left_name} returned "
            f"{type(left).__name__}, {right_name} returned "
            f"{type(right).__name__}.",
            left_name=left_name,
            right_name=right_name,
        )

    # Compare pydantic models via model_dump().
    if isinstance(left, BaseModel) and isinstance(right, BaseModel):
        left_dict = left.model_dump()
        right_dict = right.model_dump()

        if left_dict == right_dict:
            return

        differences = _find_dict_differences(
            left_dict, right_dict, left_name, right_name,
        )
        diff_text = _format_differences(differences, left_name, right_name)

        raise ResultMismatchError(
            f"Machine results diverged:\n{diff_text}",
            left_name=left_name,
            right_name=right_name,
            differences=differences,
        )

    # Fallback: compare plain values via ==.
    if left == right:
        return

    raise ResultMismatchError(
        f"Machine results diverged: "
        f"{left_name}={left!r} vs {right_name}={right!r}",
        left_name=left_name,
        right_name=right_name,
    )
