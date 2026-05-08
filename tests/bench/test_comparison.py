# tests/bench/test_comparison.py
"""
Tests for ``compare_results`` and ``ResultMismatchError``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verify cross-machine result comparison: pydantic models compared field-wise via
``model_dump``, type mismatches surfaced before field diff, plain ``==`` fallback
for non-models, and structured error payloads (names, ``differences``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    left_result, right_result  +  machine labels
              |
              v
    compare_results(left, left_name, right, right_name)
              |
              +--> same type + BaseModel  ->  per-field diff
              +--> type clash            ->  ResultMismatchError (no diffs)
              +--> other                 ->  equality / repr-based mismatch

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``ResultMismatchError`` subclasses ``AssertionError`` for pytest ergonomics.

"""

import pytest
from pydantic import BaseModel

from action_machine.testing.comparison import ResultMismatchError, compare_results

# ─────────────────────────────────────────────────────────────────────────────
# Helper models defined inside the test file — intentionally simple,
# not part of the shared domain. Used only to exercise compare_results logic.
# ─────────────────────────────────────────────────────────────────────────────


class _OrderResult(BaseModel):
    """Pydantic model with two fields for comparison tests."""
    order_id: str
    total: float


class _PingResult(BaseModel):
    """Different pydantic model to trigger type-mismatch branch."""
    message: str


# ═════════════════════════════════════════════════════════════════════════════
# Identical results — no error expected
# ═════════════════════════════════════════════════════════════════════════════


class TestIdenticalResults:
    """Verify that compare_results passes silently when results match."""

    def test_identical_pydantic_models(self) -> None:
        """Two pydantic objects with the same field values produce no error."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = _OrderResult(order_id="ORD-1", total=100.0)

        # Act — should not raise
        compare_results(left, "AsyncMachine", right, "SyncMachine")

    def test_identical_plain_objects(self) -> None:
        """Two equal plain dicts produce no error via fallback equality."""
        compare_results(
            {"key": "value"}, "AsyncMachine",
            {"key": "value"}, "SyncMachine",
        )

    def test_identical_strings(self) -> None:
        """Two equal strings produce no error via fallback equality."""
        compare_results("hello", "Async", "hello", "Sync")


# ═════════════════════════════════════════════════════════════════════════════
# Diverging pydantic results
# ═════════════════════════════════════════════════════════════════════════════


class TestDivergingPydantic:
    """Verify detailed field-level error reporting for pydantic models."""

    def test_single_field_difference(self) -> None:
        """One differing field is listed in the error message and differences attribute."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = _OrderResult(order_id="ORD-2", total=100.0)

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "AsyncMachine", right, "SyncMachine")

        # Assert — error contains the differing field name
        err = exc_info.value
        assert "order_id" in str(err)
        assert err.left_name == "AsyncMachine"
        assert err.right_name == "SyncMachine"
        assert len(err.differences) == 1
        assert err.differences[0][0] == "order_id"

    def test_multiple_field_differences(self) -> None:
        """All differing fields are reported, not just the first one."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = _OrderResult(order_id="ORD-2", total=999.0)

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "A", right, "B")

        err = exc_info.value
        field_names = {d[0] for d in err.differences}
        assert "order_id" in field_names
        assert "total" in field_names


# ═════════════════════════════════════════════════════════════════════════════
# Type mismatch
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeMismatch:
    """Verify that different result types are caught before field comparison."""

    def test_different_pydantic_types(self) -> None:
        """Two different pydantic model types trigger a type-mismatch error."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = _PingResult(message="pong")

        with pytest.raises(ResultMismatchError, match="Result types differ"):
            compare_results(left, "Async", right, "Sync")

    def test_pydantic_vs_plain(self) -> None:
        """A pydantic model vs a plain dict triggers a type-mismatch error."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = {"order_id": "ORD-1", "total": 100.0}

        with pytest.raises(ResultMismatchError, match="Result types differ"):
            compare_results(left, "Async", right, "Sync")


# ═════════════════════════════════════════════════════════════════════════════
# Diverging non-pydantic results (fallback ==)
# ═════════════════════════════════════════════════════════════════════════════


class TestDivergingPlain:
    """Verify fallback comparison for non-pydantic objects."""

    def test_different_dicts(self) -> None:
        """Two non-equal dicts raise ResultMismatchError with repr of both."""
        with pytest.raises(ResultMismatchError, match="diverged"):
            compare_results({"a": 1}, "Left", {"a": 2}, "Right")

    def test_different_strings(self) -> None:
        """Two non-equal strings raise ResultMismatchError."""
        with pytest.raises(ResultMismatchError):
            compare_results("hello", "L", "world", "R")


# ═════════════════════════════════════════════════════════════════════════════
# ResultMismatchError attributes
# ═════════════════════════════════════════════════════════════════════════════


class TestErrorAttributes:
    """Verify that ResultMismatchError carries structured data for programmatic access."""

    def test_differences_empty_for_type_mismatch(self) -> None:
        """Type-mismatch errors have an empty differences list."""
        left = _OrderResult(order_id="ORD-1", total=100.0)
        right = _PingResult(message="pong")

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "A", right, "B")

        assert exc_info.value.differences == []

    def test_is_assertion_error(self) -> None:
        """ResultMismatchError inherits AssertionError so pytest shows it as assertion failure."""
        with pytest.raises(AssertionError):
            compare_results("x", "A", "y", "B")
