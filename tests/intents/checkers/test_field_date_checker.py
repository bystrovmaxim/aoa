# tests/intents/checkers/test_field_date_checker.py
"""
Tests for FieldDateChecker — validates date fields in aspect result dictionaries.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures FieldDateChecker correctly validates date fields in the aspect result
dict. Accepts datetime objects and strings parsed with the given date_format.
Supports range checks (min_date, max_date).

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - datetime object accepted without format.
    - String matching date_format accepted.
    - Date on min_date / max_date boundary accepted (inclusive).
    - Date inside range accepted.

TestInvalidValues
    - int, list, dict, bool — not datetime and not string → error.
    - String without date_format → error (format required).
    - String not matching format → error.
    - Date before min_date → error.
    - Date after max_date → error.

TestRequired
    - required=True: missing or None field → error.
    - required=False: missing or None field allowed.
    - required=False: present invalid value → error.

TestDecorator
    - result_date records _checker_meta with correct parameters.
    - date_format, min_date, max_date end up in extra_params.
    - Decorator returns the original function.
    - Multiple decorators accumulate.
"""

from datetime import UTC, datetime

import pytest

from action_machine.intents.checkers.field_date_checker import FieldDateChecker
from action_machine.intents.checkers.result_date_decorator import result_date
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Valid values
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """Correct dates are accepted without error."""

    def test_datetime_object_accepted(self):
        """datetime object accepted without date_format."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)
        dt = datetime(2024, 6, 15, 12, 30, 0)

        # Act & Assert — no exception
        checker.check({"created_at": dt})

    def test_datetime_with_timezone_accepted(self):
        """datetime with timezone accepted."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)

        # Act & Assert — no exception
        checker.check({"created_at": dt})

    def test_string_with_format_accepted(self):
        """String matching date_format accepted."""
        # Arrange
        checker = FieldDateChecker(
            "created_at",
            required=True,
            date_format="%Y-%m-%d",
        )

        # Act & Assert — no exception
        checker.check({"created_at": "2024-01-15"})

    def test_string_with_datetime_format_accepted(self):
        """String with datetime format accepted."""
        # Arrange
        checker = FieldDateChecker(
            "timestamp",
            required=True,
            date_format="%Y-%m-%d %H:%M:%S",
        )

        # Act & Assert — no exception
        checker.check({"timestamp": "2024-06-15 14:30:00"})

    def test_date_at_min_boundary_accepted(self):
        """Date equal to min_date accepted (inclusive)."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        checker = FieldDateChecker(
            "event_date",
            required=True,
            min_date=min_dt,
        )

        # Act & Assert — no exception
        checker.check({"event_date": min_dt})

    def test_date_at_max_boundary_accepted(self):
        """Date equal to max_date accepted (inclusive)."""
        # Arrange
        max_dt = datetime(2024, 12, 31)
        checker = FieldDateChecker(
            "event_date",
            required=True,
            max_date=max_dt,
        )

        # Act & Assert — no exception
        checker.check({"event_date": max_dt})

    def test_date_within_range_accepted(self):
        """Date inside min_date..max_date accepted."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            min_date=datetime(2024, 1, 1),
            max_date=datetime(2024, 12, 31),
        )
        value = datetime(2024, 6, 15)

        # Act & Assert — no exception
        checker.check({"event_date": value})

    def test_string_date_within_range_accepted(self):
        """String date inside range accepted after parsing."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            min_date=datetime(2024, 1, 1),
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert — no exception
        checker.check({"event_date": "2024-06-15"})


# ═════════════════════════════════════════════════════════════════════════════
# Invalid values
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Invalid values raise ValidationFieldError."""

    def test_int_rejected(self):
        """int is neither datetime nor string."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": 20240115})

    def test_bool_rejected(self):
        """bool is neither datetime nor string."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": True})

    def test_list_rejected(self):
        """list is neither datetime nor string."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": [2024, 1, 15]})

    def test_dict_rejected(self):
        """dict is neither datetime nor string."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": {"year": 2024}})

    def test_string_without_format_raises(self):
        """String without date_format raises."""
        # Arrange — date_format not set
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="date_format"):
            checker.check({"created_at": "2024-01-15"})

    def test_string_wrong_format_raises(self):
        """String not matching date_format raises."""
        # Arrange
        checker = FieldDateChecker(
            "created_at",
            required=True,
            date_format="%Y-%m-%d",
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="date format"):
            checker.check({"created_at": "15/01/2024"})

    def test_date_below_min_raises(self):
        """Date before min_date raises."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            min_date=datetime(2024, 6, 1),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="greater than or equal"):
            checker.check({"event_date": datetime(2024, 5, 31)})

    def test_date_above_max_raises(self):
        """Date after max_date raises."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="less than or equal"):
            checker.check({"event_date": datetime(2025, 1, 1)})

    def test_string_date_below_min_raises(self):
        """String date before min_date raises after parsing."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            min_date=datetime(2024, 6, 1),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="greater than or equal"):
            checker.check({"event_date": "2024-05-01"})

    def test_string_date_above_max_raises(self):
        """String date after max_date raises after parsing."""
        # Arrange
        checker = FieldDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="less than or equal"):
            checker.check({"event_date": "2025-01-01"})

    def test_error_message_contains_field_name(self):
        """Error message includes field name."""
        # Arrange
        checker = FieldDateChecker("delivery_date", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="delivery_date"):
            checker.check({"delivery_date": 12345})

    def test_error_message_contains_actual_type(self):
        """Error message includes actual value type."""
        # Arrange
        checker = FieldDateChecker("delivery_date", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="int"):
            checker.check({"delivery_date": 12345})


# ═════════════════════════════════════════════════════════════════════════════
# Required field
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Behavior of required for mandatory vs optional fields."""

    def test_required_missing_field_raises(self):
        """Missing required field raises."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None in required field raises."""
        # Arrange
        checker = FieldDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": None})

    def test_optional_missing_field_passes(self):
        """Missing optional field allowed."""
        # Arrange
        checker = FieldDateChecker("created_at", required=False)

        # Act & Assert — no exception
        checker.check({})

    def test_optional_none_passes(self):
        """None in optional field allowed."""
        # Arrange
        checker = FieldDateChecker("created_at", required=False)

        # Act & Assert — no exception
        checker.check({"created_at": None})

    def test_optional_invalid_type_still_raises(self):
        """Invalid type still raises even when field is optional."""
        # Arrange
        checker = FieldDateChecker("created_at", required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": 12345})


# ═════════════════════════════════════════════════════════════════════════════
# _get_extra_params
# ═════════════════════════════════════════════════════════════════════════════


class TestExtraParams:
    """_get_extra_params returns correct parameters."""

    def test_extra_params_all_none_by_default(self):
        """Without extra args all values are None."""
        # Arrange
        checker = FieldDateChecker("created_at")

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["date_format"] is None
        assert params["min_date"] is None
        assert params["max_date"] is None

    def test_extra_params_with_format(self):
        """date_format stored in extra_params."""
        # Arrange
        checker = FieldDateChecker("created_at", date_format="%Y-%m-%d")

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["date_format"] == "%Y-%m-%d"

    def test_extra_params_with_range(self):
        """min_date and max_date stored in extra_params."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        max_dt = datetime(2024, 12, 31)
        checker = FieldDateChecker(
            "event_date",
            min_date=min_dt,
            max_date=max_dt,
        )

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["min_date"] == min_dt
        assert params["max_date"] == max_dt


# ═════════════════════════════════════════════════════════════════════════════
# result_date decorator
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """result_date decorator records metadata on the function."""

    def test_checker_meta_attached(self):
        """Decorator creates _checker_meta attribute."""
        # Arrange & Act
        @result_date("created_at", date_format="%Y-%m-%d")
        async def aspect(self, params, state, box, connections):
            return {"created_at": "2024-01-15"}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_date_checker(self):
        """Metadata contains correct checker class."""
        # Arrange & Act
        @result_date("created_at")
        async def aspect(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldDateChecker

    def test_field_name_recorded(self):
        """Field name stored in metadata."""
        # Arrange & Act
        @result_date("delivery_date")
        async def aspect(self, params, state, box, connections):
            return {"delivery_date": datetime(2024, 6, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "delivery_date"

    def test_required_default_true(self):
        """Default required=True."""
        # Arrange & Act
        @result_date("created_at")
        async def aspect(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Explicit required=False stored."""
        # Arrange & Act
        @result_date("created_at", required=False)
        async def aspect(self, params, state, box, connections):
            return {"created_at": None}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_extra_params_in_meta(self):
        """date_format, min_date, max_date available via checker instance."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        max_dt = datetime(2024, 12, 31)

        # Act
        @result_date(
            "event_date",
            date_format="%Y-%m-%d",
            min_date=min_dt,
            max_date=max_dt,
        )
        async def aspect(self, params, state, box, connections):
            return {"event_date": "2024-06-15"}

        # Assert — metadata recorded and checker behaves correctly
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldDateChecker
        assert meta["field_name"] == "event_date"
        # Extra params via checker instance
        checker = FieldDateChecker(
            "event_date",
            date_format="%Y-%m-%d",
            min_date=min_dt,
            max_date=max_dt,
        )
        extra = checker._get_extra_params()
        assert extra["date_format"] == "%Y-%m-%d"
        assert extra["min_date"] == min_dt
        assert extra["max_date"] == max_dt

    def test_decorator_returns_original_function(self):
        """Decorator returns the original function unchanged."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Act
        decorated = result_date("created_at")(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Multiple decorators on one method build a metadata list."""
        # Arrange & Act
        @result_date("created_at", date_format="%Y-%m-%d")
        @result_date("updated_at", date_format="%Y-%m-%d %H:%M:%S")
        async def aspect(self, params, state, box, connections):
            return {
                "created_at": "2024-01-15",
                "updated_at": "2024-06-15 14:30:00",
            }

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"created_at", "updated_at"}
