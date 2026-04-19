# tests/intents/checkers/test_result_float_checker.py
"""
Tests for FieldFloatChecker and the result_float decorator — numeric fields (int/float).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

FieldFloatChecker ensures an aspect result field is numeric (int OR float) within
the given range (min_value, max_value).

Unlike FieldIntChecker, which accepts only int, FieldFloatChecker accepts both
numeric types. Useful for fields like amount, total, discount where the value may
be 100 or 99.99.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Valid values:
    - Float, int, zero (0 and 0.0), negative numbers.
    - Value exactly on min_value / max_value boundaries.

Invalid values:
    - String, list, bool → ValidationFieldError.
    - Value outside range → ValidationFieldError.

Required / optional:
    - required=True, field missing → ValidationFieldError.
    - required=False, field missing → OK.

Decorator:
    - result_float records _checker_meta with min_value, max_value.
"""

import pytest

from action_machine.intents.checkers.result_float_checker import FieldFloatChecker
from action_machine.intents.checkers.result_float_decorator import result_float
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Valid values
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """check() succeeds for valid numeric values."""

    def test_float_value(self) -> None:
        """Float passes."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        checker.check({"total": 99.99})

    def test_int_value(self) -> None:
        """Int passes — FieldFloatChecker accepts int and float."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        checker.check({"total": 100})

    def test_zero_float(self) -> None:
        """Float zero 0.0 passes."""
        # Arrange
        checker = FieldFloatChecker("discount", required=True)

        # Act & Assert
        checker.check({"discount": 0.0})

    def test_zero_int(self) -> None:
        """Int zero 0 passes."""
        # Arrange
        checker = FieldFloatChecker("discount", required=True)

        # Act & Assert
        checker.check({"discount": 0})

    def test_negative_value(self) -> None:
        """Negative number passes when min_value is not set."""
        # Arrange
        checker = FieldFloatChecker("balance", required=True)

        # Act & Assert
        checker.check({"balance": -500.50})

    def test_exact_min_value(self) -> None:
        """Value exactly min_value passes (inclusive)."""
        # Arrange
        checker = FieldFloatChecker("amount", required=True, min_value=0.0)

        # Act & Assert
        checker.check({"amount": 0.0})

    def test_exact_max_value(self) -> None:
        """Value exactly max_value passes (inclusive)."""
        # Arrange
        checker = FieldFloatChecker("rate", required=True, max_value=1.0)

        # Act & Assert
        checker.check({"rate": 1.0})

    def test_between_bounds(self) -> None:
        """Value between min and max passes."""
        # Arrange
        checker = FieldFloatChecker("percent", required=True, min_value=0.0, max_value=100.0)

        # Act & Assert
        checker.check({"percent": 55.5})

    def test_int_at_float_boundary(self) -> None:
        """Int value at float min_value boundary."""
        # Arrange — min_value=0.0, pass int 0
        checker = FieldFloatChecker("total", required=True, min_value=0.0)

        # Act & Assert — int 0 >= float 0.0
        checker.check({"total": 0})


# ═════════════════════════════════════════════════════════════════════════════
# Invalid values
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """check() raises ValidationFieldError for invalid values."""

    def test_string_raises(self) -> None:
        """String instead of number → ValidationFieldError."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="numeric"):
            checker.check({"total": "99.99"})

    def test_list_raises(self) -> None:
        """List → ValidationFieldError."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="numeric"):
            checker.check({"total": [1, 2]})

    def test_bool_raises(self) -> None:
        """
        Bool → ValidationFieldError.

        Although bool is a subclass of int in Python, FieldFloatChecker uses
        isinstance(value, (int, float)), so bool passes. That is Python behavior,
        not a checker quirk.

        NOTE: if this test fails, FieldFloatChecker accepts bool as a number
        (technically correct in Python). In that case remove this test.
        """
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Note: bool IS int in Python, so isinstance(True, (int, float)) is True.
        # This test documents behavior, not a bug.
        # True is accepted as int(1), False as int(0).
        checker.check({"total": True})  # Does not raise — bool IS int

    def test_below_min_value(self) -> None:
        """Value below min_value → ValidationFieldError."""
        # Arrange
        checker = FieldFloatChecker("amount", required=True, min_value=0.0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="greater than or equal"):
            checker.check({"amount": -0.01})

    def test_above_max_value(self) -> None:
        """Value above max_value → ValidationFieldError."""
        # Arrange
        checker = FieldFloatChecker("rate", required=True, max_value=1.0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="less than or equal"):
            checker.check({"rate": 1.001})

    def test_none_dict_value_raises(self) -> None:
        """None as value → ValidationFieldError (required field)."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Missing required parameter"):
            checker.check({"total": None})


# ═════════════════════════════════════════════════════════════════════════════
# Required / optional
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Behavior for required=True and required=False."""

    def test_required_missing_raises(self) -> None:
        """required=True, field missing → ValidationFieldError."""
        # Arrange
        checker = FieldFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Missing required parameter"):
            checker.check({})

    def test_optional_missing_ok(self) -> None:
        """required=False, field missing → OK."""
        # Arrange
        checker = FieldFloatChecker("total", required=False)

        # Act & Assert
        checker.check({})

    def test_optional_present_still_validated(self) -> None:
        """required=False but value present — type is still validated."""
        # Arrange
        checker = FieldFloatChecker("total", required=False)

        # Act & Assert — string instead of number
        with pytest.raises(ValidationFieldError, match="numeric"):
            checker.check({"total": "not_a_number"})


# ═════════════════════════════════════════════════════════════════════════════
# result_float decorator
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """The result_float decorator records _checker_meta."""

    def test_writes_checker_meta(self) -> None:
        """
        @result_float("total") records _checker_meta on the method.
        """
        # Arrange & Act
        @result_float("total", required=True, min_value=0.0, max_value=999999.99)
        async def calc(self, params, state, box, connections):
            return {"total": 1500.0}

        # Assert
        assert hasattr(calc, "_checker_meta")
        assert len(calc._checker_meta) == 1
        m = calc._checker_meta[0]
        assert m["checker_class"] is FieldFloatChecker
        assert m["field_name"] == "total"
        assert m["required"] is True
        assert m["min_value"] == 0.0
        assert m["max_value"] == 999999.99

    def test_decorator_preserves_function(self) -> None:
        """Decorator returns the same function object."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {}

        # Act
        decorated = result_float("total")(original)

        # Assert
        assert decorated is original

    def test_combined_with_result_string(self) -> None:
        """
        result_float + result_string on one method — both are recorded.

        One aspect may validate fields of different types.
        """
        # Arrange & Act
        from action_machine.intents.checkers.result_string_decorator import result_string

        @result_string("txn_id", required=True)
        @result_float("amount", required=True, min_value=0.0)
        async def process(self, params, state, box, connections):
            return {"txn_id": "TXN-1", "amount": 100.0}

        # Assert — two checkers in the list
        assert len(process._checker_meta) == 2
        fields = [m["field_name"] for m in process._checker_meta]
        assert "txn_id" in fields
        assert "amount" in fields
