# tests/intents/checkers/test_result_int_checker.py
"""
Tests for ResultIntChecker and the result_int decorator — integer fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ResultIntChecker ensures an aspect result field is an integer (int) within the
given range (min_value, max_value).

Float, bool, and strings are rejected — only isinstance(value, int) passes.
In Python, bool is a subclass of int, but ResultIntChecker uses
isinstance(value, int), so bool passes. To exclude bool, use ResultBoolChecker
separately.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Valid values:
    - Positive int, negative int, zero.
    - Value exactly on min_value / max_value boundaries.

Invalid values:
    - Float instead of int → ValidationFieldError.
    - String instead of int → ValidationFieldError.
    - Value below min_value → ValidationFieldError.
    - Value above max_value → ValidationFieldError.

Required / optional:
    - required=True, field missing → ValidationFieldError.
    - required=False, field missing → OK.

Decorator:
    - result_int records _checker_meta with min_value, max_value.
"""

import pytest

from action_machine.intents.checkers.result_int_checker import ResultIntChecker, result_int
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Valid values
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """check() succeeds for valid integer values."""

    def test_positive_int(self) -> None:
        """Positive integer passes."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        checker.check({"count": 42})

    def test_negative_int(self) -> None:
        """Negative integer passes."""
        # Arrange
        checker = ResultIntChecker("offset", required=True)

        # Act & Assert
        checker.check({"offset": -10})

    def test_zero(self) -> None:
        """Zero passes as a valid integer."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        checker.check({"count": 0})

    def test_exact_min_value(self) -> None:
        """Value exactly min_value passes (inclusive)."""
        # Arrange
        checker = ResultIntChecker("age", required=True, min_value=0)

        # Act & Assert
        checker.check({"age": 0})

    def test_exact_max_value(self) -> None:
        """Value exactly max_value passes (inclusive)."""
        # Arrange
        checker = ResultIntChecker("score", required=True, max_value=100)

        # Act & Assert
        checker.check({"score": 100})

    def test_between_min_and_max(self) -> None:
        """Value between min and max passes."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        checker.check({"level": 5})

    def test_large_int(self) -> None:
        """Very large integer passes."""
        # Arrange
        checker = ResultIntChecker("big", required=True)

        # Act & Assert
        checker.check({"big": 10**18})


# ═════════════════════════════════════════════════════════════════════════════
# Invalid values
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """check() raises ValidationFieldError for invalid values."""

    def test_float_raises(self) -> None:
        """Float instead of int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="integer"):
            checker.check({"count": 3.14})

    def test_string_raises(self) -> None:
        """String instead of int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="integer"):
            checker.check({"count": "42"})

    def test_list_raises(self) -> None:
        """List instead of int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="integer"):
            checker.check({"count": [1, 2, 3]})

    def test_below_min_value(self) -> None:
        """Value below min_value → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("age", required=True, min_value=0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="greater than or equal to 0"):
            checker.check({"age": -1})

    def test_above_max_value(self) -> None:
        """Value above max_value → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("score", required=True, max_value=100)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="less than or equal to 100"):
            checker.check({"score": 101})

    def test_below_min_with_both_bounds(self) -> None:
        """Value below min when both min and max are set."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="greater than or equal to 1"):
            checker.check({"level": 0})

    def test_above_max_with_both_bounds(self) -> None:
        """Value above max when both min and max are set."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="less than or equal to 10"):
            checker.check({"level": 11})


# ═════════════════════════════════════════════════════════════════════════════
# Required / optional
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Behavior for required=True and required=False."""

    def test_required_missing_raises(self) -> None:
        """required=True, field missing → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Missing required parameter"):
            checker.check({})

    def test_required_none_raises(self) -> None:
        """required=True, field=None → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Missing required parameter"):
            checker.check({"count": None})

    def test_optional_missing_ok(self) -> None:
        """required=False, field missing → OK."""
        # Arrange
        checker = ResultIntChecker("count", required=False)

        # Act & Assert
        checker.check({})

    def test_optional_present_still_validated(self) -> None:
        """required=False but field present — type is still validated."""
        # Arrange
        checker = ResultIntChecker("count", required=False)

        # Act & Assert — string instead of int → error
        with pytest.raises(ValidationFieldError, match="integer"):
            checker.check({"count": "not_int"})


# ═════════════════════════════════════════════════════════════════════════════
# result_int decorator
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """The result_int decorator records _checker_meta."""

    def test_writes_checker_meta(self) -> None:
        """
        @result_int("count") records _checker_meta on the method.
        """
        # Arrange & Act
        @result_int("count", required=True, min_value=0, max_value=1000)
        async def calc(self, params, state, box, connections):
            return {"count": 42}

        # Assert
        assert hasattr(calc, "_checker_meta")
        assert len(calc._checker_meta) == 1
        m = calc._checker_meta[0]
        assert m["checker_class"] is ResultIntChecker
        assert m["field_name"] == "count"
        assert m["required"] is True
        assert m["min_value"] == 0
        assert m["max_value"] == 1000

    def test_decorator_preserves_function(self) -> None:
        """Decorator returns the same function object."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {}

        # Act
        decorated = result_int("count")(original)

        # Assert
        assert decorated is original

    def test_default_params(self) -> None:
        """Defaults: required=True, min_value=None, max_value=None."""
        # Arrange & Act
        @result_int("count")
        async def calc(self, params, state, box, connections):
            return {"count": 1}

        # Assert
        m = calc._checker_meta[0]
        assert m["required"] is True
        assert m["min_value"] is None
        assert m["max_value"] is None
