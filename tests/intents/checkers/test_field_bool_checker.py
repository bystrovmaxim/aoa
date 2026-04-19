# tests/intents/checkers/test_field_bool_checker.py
"""
Tests for FieldBoolChecker — validates boolean fields in aspect results.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures FieldBoolChecker correctly validates boolean values in the aspect
result dict. Only True and False are accepted — numbers (0, 1), strings
("true", "false"), and other types are rejected.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - True and False accepted without error.

TestInvalidValues
    - ints (0, 1) — not bool → error.
    - strings ("true", "false") — not bool → error.
    - None with required=True → error.
    - list, dict — not bool → error.

TestRequired
    - required=True: missing or None field → error.
    - required=False: missing or None field allowed.
    - required=False: present non-bool still → error.

TestDecorator
    - result_bool records _checker_meta on the function.
    - checker_class, field_name, required stored correctly.
    - Decorator returns the original function unchanged.
    - Multiple decorators on one method grow the list.
"""

import pytest

from action_machine.intents.checkers.result_bool_decorator import FieldBoolChecker, result_bool
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Valid values
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """True and False are accepted without error."""

    def test_true_accepted(self):
        """True is a valid boolean."""
        # Arrange
        checker = FieldBoolChecker("is_active", required=True)

        # Act & Assert — no exception
        checker.check({"is_active": True})

    def test_false_accepted(self):
        """False is a valid boolean."""
        # Arrange
        checker = FieldBoolChecker("is_deleted", required=True)

        # Act & Assert — no exception
        checker.check({"is_deleted": False})


# ═════════════════════════════════════════════════════════════════════════════
# Invalid values
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Non-bool types raise ValidationFieldError."""

    def test_int_zero_rejected(self):
        """int 0 is not bool despite being falsy."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": 0})

    def test_int_one_rejected(self):
        """int 1 is not bool despite being truthy."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": 1})

    def test_string_true_rejected(self):
        """String 'true' is not bool."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "true"})

    def test_string_false_rejected(self):
        """String 'false' is not bool."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "false"})

    def test_list_rejected(self):
        """List is not bool."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": [True]})

    def test_dict_rejected(self):
        """Dict is not bool."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": {"value": True}})

    def test_none_rejected_when_required(self):
        """None with required=True raises."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": None})

    def test_error_message_contains_field_name(self):
        """Error message includes field name."""
        # Arrange
        checker = FieldBoolChecker("is_valid", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="is_valid"):
            checker.check({"is_valid": "yes"})

    def test_error_message_contains_actual_type(self):
        """Error message includes actual value type."""
        # Arrange
        checker = FieldBoolChecker("is_valid", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="str"):
            checker.check({"is_valid": "yes"})


# ═════════════════════════════════════════════════════════════════════════════
# Required field
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Behavior of required for mandatory vs optional fields."""

    def test_required_missing_field_raises(self):
        """Missing required field raises."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None in required field raises."""
        # Arrange
        checker = FieldBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": None})

    def test_optional_missing_field_passes(self):
        """Missing optional field allowed."""
        # Arrange
        checker = FieldBoolChecker("flag", required=False)

        # Act & Assert — no exception
        checker.check({})

    def test_optional_none_passes(self):
        """None in optional field allowed."""
        # Arrange
        checker = FieldBoolChecker("flag", required=False)

        # Act & Assert — no exception
        checker.check({"flag": None})

    def test_optional_invalid_type_still_raises(self):
        """Non-bool value still raises when field is optional but present."""
        # Arrange
        checker = FieldBoolChecker("flag", required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "true"})


# ═════════════════════════════════════════════════════════════════════════════
# result_bool decorator
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """result_bool decorator records metadata on the function."""

    def test_checker_meta_attached(self):
        """Decorator creates _checker_meta attribute."""

        # Arrange & Act
        @result_bool("is_active")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_bool_checker(self):
        """Metadata contains correct checker class."""

        # Arrange & Act
        @result_bool("is_active")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldBoolChecker

    def test_field_name_recorded(self):
        """Field name stored in metadata."""

        # Arrange & Act
        @result_bool("is_deleted")
        async def aspect(self, params, state, box, connections):
            return {"is_deleted": False}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "is_deleted"

    def test_required_default_true(self):
        """Default required=True."""

        # Arrange & Act
        @result_bool("flag")
        async def aspect(self, params, state, box, connections):
            return {"flag": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Explicit required=False stored."""

        # Arrange & Act
        @result_bool("flag", required=False)
        async def aspect(self, params, state, box, connections):
            return {"flag": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_decorator_returns_original_function(self):
        """Decorator returns the original function unchanged."""

        # Arrange
        async def original(self, params, state, box, connections):
            return {"flag": True}

        # Act
        decorated = result_bool("flag")(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Multiple decorators on one method build a metadata list."""

        # Arrange & Act
        @result_bool("is_active")
        @result_bool("is_verified")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True, "is_verified": False}

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"is_active", "is_verified"}
