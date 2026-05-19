# tests/intents/checkers/test_field_instance_checker.py
"""
Tests for FieldInstanceChecker — validates values against expected classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures FieldInstanceChecker correctly validates that a value in the aspect
result dict is an instance of the given class (or one of several if a tuple is
passed). Uses isinstance(), so inheritance is supported.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - Instance of exact class accepted.
    - Instance of subclass accepted (inheritance).
    - Tuple of classes — instance of any member accepted.
    - Built-in types (dict, list, str) accepted.

TestInvalidValues
    - Instance of wrong class → error.
    - Primitive instead of custom class → error.
    - Tuple of classes — instance outside tuple → error.
    - Error message includes field name and actual type.
    - Tuple error message includes all expected class names.

TestRequired
    - required=True: missing or None field → error.
    - required=False: missing or None field allowed.
    - required=False: wrong type when present → error.

TestNoNone
    - no_none=True: explicit None rejected.
    - no_none=False: explicit None follows optional/required + isinstance rules.

TestValueCheck
    - value_check True/False after isinstance.
    - value_check skipped on wrong type, no_none, or missing field.

TestExtraParams
    - _get_extra_params returns expected_class and no_none.

TestDecorator
    - result_instance records _checker_meta with correct parameters.
    - expected_class (single or tuple) in extra_params.
    - Decorator returns the original function.
    - Multiple decorators accumulate.
"""

from typing import Any

import pytest

from aoa.action_machine.exceptions import ValidationFieldError
from aoa.action_machine.intents.checkers.result_instance_decorator import FieldInstanceChecker, result_instance

# ═════════════════════════════════════════════════════════════════════════════
# Helper classes for tests
# ═════════════════════════════════════════════════════════════════════════════


class _User:
    """Simple user class for isinstance checks."""

    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name


class _AdminUser(_User):
    """Subclass — verifies isinstance inheritance."""

    def __init__(self, user_id: int, name: str, level: int) -> None:
        super().__init__(user_id, name)
        self.level = level


class _Order:
    """Order class — used for type mismatch tests."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class _Payment:
    """Payment class — used in tuple of expected classes."""

    def __init__(self, amount: float) -> None:
        self.amount = amount


def _bool_value_check(value: Any) -> bool:
    return bool(value)


def _always_true_value_check(_value: Any) -> bool:
    return True


def _always_false_value_check(_value: Any) -> bool:
    return False


# ═════════════════════════════════════════════════════════════════════════════
# Valid values
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """Instances of correct classes are accepted without error."""

    def test_exact_class_accepted(self):
        """Instance of exact class accepted."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)
        user = _User(user_id=1, name="Alice")

        # Act & Assert — no exception
        checker.check({"user": user})

    def test_subclass_accepted(self):
        """Subclass instance accepted (isinstance follows inheritance)."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)
        admin = _AdminUser(user_id=2, name="Bob", level=5)

        # Act & Assert — no exception
        checker.check({"user": admin})

    def test_tuple_of_classes_first_match(self):
        """Tuple of classes — instance of first class accepted."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        user = _User(user_id=1, name="Alice")

        # Act & Assert — no exception
        checker.check({"entity": user})

    def test_tuple_of_classes_second_match(self):
        """Tuple of classes — instance of second class accepted."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        order = _Order(order_id="ORD-001")

        # Act & Assert — no exception
        checker.check({"entity": order})

    def test_tuple_subclass_match(self):
        """Tuple of classes — subclass of a member accepted."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        admin = _AdminUser(user_id=3, name="Carol", level=10)

        # Act & Assert — no exception
        checker.check({"entity": admin})

    def test_builtin_dict_accepted(self):
        """Built-in dict as expected_class accepted."""
        # Arrange
        checker = FieldInstanceChecker("data", dict, required=True)

        # Act & Assert — no exception
        checker.check({"data": {"key": "value"}})

    def test_builtin_list_accepted(self):
        """Built-in list as expected_class accepted."""
        # Arrange
        checker = FieldInstanceChecker("items", list, required=True)

        # Act & Assert — no exception
        checker.check({"items": [1, 2, 3]})

    def test_builtin_str_accepted(self):
        """Built-in str as expected_class accepted."""
        # Arrange
        checker = FieldInstanceChecker("label", str, required=True)

        # Act & Assert — no exception
        checker.check({"label": "hello"})

    def test_tuple_of_builtins_accepted(self):
        """Tuple of built-ins — dict or list."""
        # Arrange
        checker = FieldInstanceChecker("data", (dict, list), required=True)

        # Act & Assert — both variants pass
        checker.check({"data": {"a": 1}})
        checker.check({"data": [1, 2]})


# ═════════════════════════════════════════════════════════════════════════════
# Invalid values
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Wrong types raise ValidationFieldError."""

    def test_wrong_class_rejected(self):
        """Instance of another class rejected."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)
        order = _Order(order_id="ORD-001")

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": order})

    def test_primitive_instead_of_class_rejected(self):
        """Primitive (str) instead of custom class rejected."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": "not a user"})

    def test_int_instead_of_class_rejected(self):
        """int instead of custom class rejected."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": 42})

    def test_none_when_required_rejected(self):
        """None with required=True raises."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": None})

    def test_tuple_no_match_rejected(self):
        """Tuple of classes — instance outside tuple rejected."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"entity": payment})

    def test_dict_instead_of_custom_class_rejected(self):
        """dict instead of custom class rejected."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": {"user_id": 1, "name": "Alice"}})

    def test_error_message_single_class_contains_field_name(self):
        """Single-class error message includes field name."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="user"):
            checker.check({"user": "not a user"})

    def test_error_message_single_class_contains_expected_name(self):
        """Error message includes expected class name."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_User"):
            checker.check({"user": "not a user"})

    def test_error_message_single_class_contains_actual_type(self):
        """Error message includes actual value type."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="str"):
            checker.check({"user": "not a user"})

    def test_error_message_tuple_contains_all_class_names(self):
        """Tuple error message includes all expected class names."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_User"):
            checker.check({"entity": payment})

    def test_error_message_tuple_contains_second_class_name(self):
        """Tuple error message includes second class name."""
        # Arrange
        checker = FieldInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_Order"):
            checker.check({"entity": payment})


# ═════════════════════════════════════════════════════════════════════════════
# Required field
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Behavior of required for mandatory vs optional fields."""

    def test_required_missing_field_raises(self):
        """Missing required field raises."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None in required field raises."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": None})

    def test_optional_missing_field_passes(self):
        """Missing optional field allowed."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=False)

        # Act & Assert — no exception
        checker.check({})

    def test_optional_none_passes(self):
        """None in optional field allowed."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=False)

        # Act & Assert — no exception
        checker.check({"user": None})

    def test_optional_invalid_type_still_raises(self):
        """Wrong type still raises when field is optional but present."""
        # Arrange
        checker = FieldInstanceChecker("user", _User, required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": "not a user"})


# ═════════════════════════════════════════════════════════════════════════════
# no_none
# ═════════════════════════════════════════════════════════════════════════════


class TestNoNone:
    """Explicit None rejection when no_none=True."""

    def test_no_none_true_rejects_explicit_none(self):
        """required=True, no_none=True: explicit None raises."""
        checker = FieldInstanceChecker("ocel", _User, required=True, no_none=True)

        with pytest.raises(ValidationFieldError, match="must not be None"):
            checker.check({"ocel": None})

    def test_no_none_false_required_none_fails_isinstance(self):
        """required=True, no_none=False: explicit None fails type check."""
        checker = FieldInstanceChecker("ocel", _User, required=True, no_none=False)

        with pytest.raises(ValidationFieldError):
            checker.check({"ocel": None})

    def test_no_none_true_valid_value_passes(self):
        """no_none=True: valid instance accepted."""
        checker = FieldInstanceChecker("ocel", _User, required=True, no_none=True)
        user = _User(user_id=1, name="Alice")

        checker.check({"ocel": user})

    def test_required_true_missing_field_raises(self):
        """required=True: missing key raises."""
        checker = FieldInstanceChecker("ocel", _User, required=True, no_none=True)

        with pytest.raises(ValidationFieldError, match="Missing required parameter"):
            checker.check({})

    def test_required_false_missing_field_passes(self):
        """required=False: missing key allowed."""
        checker = FieldInstanceChecker("ocel", _User, required=False, no_none=True)

        checker.check({})


# ═════════════════════════════════════════════════════════════════════════════
# value_check
# ═════════════════════════════════════════════════════════════════════════════


class TestValueCheck:
    """Optional predicate after isinstance."""

    def test_value_check_true_passes(self):
        """value_check returning True accepts valid instance."""
        checker = FieldInstanceChecker(
            "x", _User, value_check=_always_true_value_check,
        )
        checker.check({"x": _User(1, "Alice")})

    def test_value_check_false_raises(self):
        """value_check returning False raises ValidationFieldError."""
        checker = FieldInstanceChecker(
            "x", _User, value_check=_always_false_value_check,
        )
        with pytest.raises(ValidationFieldError, match="failed value_check"):
            checker.check({"x": _User(1, "Alice")})

    def test_value_check_not_called_on_wrong_type(self):
        """value_check skipped when isinstance fails."""
        calls: list[Any] = []

        def track(_v: Any) -> bool:
            calls.append(1)
            return True

        checker = FieldInstanceChecker("x", _User, value_check=track)
        with pytest.raises(ValidationFieldError):
            checker.check({"x": "not a user"})
        assert calls == []

    def test_value_check_not_called_on_no_none_violation(self):
        """value_check skipped when no_none rejects explicit None."""
        calls: list[Any] = []

        def track(_v: Any) -> bool:
            calls.append(1)
            return True

        checker = FieldInstanceChecker("x", _User, no_none=True, value_check=track)
        with pytest.raises(ValidationFieldError, match="must not be None"):
            checker.check({"x": None})
        assert calls == []

    def test_value_check_not_called_when_field_missing(self):
        """value_check skipped when field is absent."""
        calls: list[Any] = []

        def track(_v: Any) -> bool:
            calls.append(1)
            return True

        checker = FieldInstanceChecker("x", _User, required=False, value_check=track)
        checker.check({})
        assert calls == []

    def test_without_value_check_unchanged(self):
        """Default value_check=None keeps prior behavior."""
        checker = FieldInstanceChecker("user", _User)
        checker.check({"user": _User(1, "Alice")})


# ═════════════════════════════════════════════════════════════════════════════
# _get_extra_params
# ═════════════════════════════════════════════════════════════════════════════


class TestExtraParams:
    """_get_extra_params returns expected_class."""

    def test_extra_params_single_class(self):
        """Single class stored in extra_params."""
        # Arrange
        checker = FieldInstanceChecker("user", _User)

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["expected_class"] is _User
        assert params["no_none"] is False

    def test_extra_params_no_none_true(self):
        """no_none flag stored in extra_params."""
        checker = FieldInstanceChecker("ocel", _User, no_none=True)

        params = checker._get_extra_params()

        assert params["no_none"] is True

    def test_extra_params_includes_value_check_when_set(self):
        """value_check callable stored in extra_params."""
        checker = FieldInstanceChecker("x", _User, value_check=_bool_value_check)

        params = checker._get_extra_params()

        assert params["value_check"] is _bool_value_check

    def test_extra_params_omits_value_check_when_none(self):
        """value_check omitted from extra_params when unset."""
        checker = FieldInstanceChecker("user", _User)

        params = checker._get_extra_params()

        assert "value_check" not in params

    def test_extra_params_tuple_of_classes(self):
        """Tuple of classes stored in extra_params."""
        # Arrange
        expected = (_User, _Order)
        checker = FieldInstanceChecker("entity", expected)

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["expected_class"] is expected


# ═════════════════════════════════════════════════════════════════════════════
# result_instance decorator
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """result_instance decorator records metadata on the function."""

    def test_checker_meta_attached(self):
        """Decorator creates _checker_meta attribute."""

        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_instance_checker(self):
        """Metadata contains correct checker class."""

        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldInstanceChecker

    def test_field_name_recorded(self):
        """Field name stored in metadata."""

        # Arrange & Act
        @result_instance("order", _Order)
        async def aspect(self, params, state, box, connections):
            return {"order": _Order("ORD-001")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "order"

    def test_required_default_true(self):
        """Default required=True."""

        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Explicit required=False stored."""

        # Arrange & Act
        @result_instance("user", _User, required=False)
        async def aspect(self, params, state, box, connections):
            return {"user": None}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_no_none_default_false(self):
        """Default no_none=False in metadata."""
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        meta = aspect._checker_meta[0]
        assert meta["no_none"] is False

    def test_no_none_true_recorded(self):
        """Explicit no_none=True stored in metadata."""
        @result_instance("ocel", _User, required=True, no_none=True)
        async def aspect(self, params, state, box, connections):
            return {"ocel": _User(1, "Alice")}

        meta = aspect._checker_meta[0]
        assert meta["no_none"] is True

    def test_value_check_recorded_in_meta(self):
        """value_check callable stored in decorator metadata."""
        @result_instance("ocel", _User, value_check=_bool_value_check)
        async def aspect(self, params, state, box, connections):
            return {"ocel": _User(1, "Alice")}

        meta = aspect._checker_meta[0]
        assert meta["value_check"] is _bool_value_check

    def test_value_check_default_none_in_meta(self):
        """Default value_check=None in metadata."""
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        meta = aspect._checker_meta[0]
        assert meta["value_check"] is None

    def test_extra_params_single_class_in_meta(self):
        """Single expected_class verified via checker instance."""

        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert — metadata recorded correctly
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldInstanceChecker
        assert meta["field_name"] == "user"
        # Extra params via checker
        checker = FieldInstanceChecker("user", _User)
        assert checker._get_extra_params()["expected_class"] is _User

    def test_extra_params_tuple_in_meta(self):
        """Tuple expected_class verified via checker instance."""
        # Arrange
        expected = (_User, _Order)

        # Act
        @result_instance("entity", expected)
        async def aspect(self, params, state, box, connections):
            return {"entity": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldInstanceChecker
        checker = FieldInstanceChecker("entity", expected)
        assert checker._get_extra_params()["expected_class"] is expected

    def test_decorator_returns_original_function(self):
        """Decorator returns the original function unchanged."""

        # Arrange
        async def original(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Act
        decorated = result_instance("user", _User)(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Multiple decorators on one method build a metadata list."""

        # Arrange & Act
        @result_instance("user", _User)
        @result_instance("order", _Order)
        async def aspect(self, params, state, box, connections):
            return {
                "user": _User(1, "Alice"),
                "order": _Order("ORD-001"),
            }

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"user", "order"}

    def test_combined_with_builtin_types(self):
        """Decorator works with built-in types (dict, list)."""

        # Arrange & Act
        @result_instance("data", (dict, list))
        async def aspect(self, params, state, box, connections):
            return {"data": {"key": "value"}}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is FieldInstanceChecker
        assert meta["field_name"] == "data"
        checker = FieldInstanceChecker("data", (dict, list))
        assert checker._get_extra_params()["expected_class"] == (dict, list)
