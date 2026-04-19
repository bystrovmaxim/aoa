# tests/model/test_resolve_types.py
"""
Tests for BaseSchema.resolve() across value types.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

resolve() returns stored values as-is — no coercion or serialization.
The type is whatever lives on the field or dict key.

resolve distinguishes “value exists but is falsy” (None, 0, False, "", [])
from “value missing”. All falsy stored values are valid results, not replaced
with default.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Strings:
    - Normal string — returned unchanged.
    - Empty string "" — valid value, not “missing”.

Numbers:
    - int — returned as int.
    - float — returned as float.
    - Zero (0, 0.0) — valid value, not “missing”.

Booleans:
    - True — returned as True.
    - False — valid value, not “missing”.

None:
    - None as field value — valid result.

Collections:
    - list — returned whole.
    - Empty list [] — valid value.
    - dict — returned whole.
    - Empty dict {} — valid value.

Nested mixed structures:
    - dict inside subclass with mixed value types.
    - Access to bool, int, list inside nested dicts.

Pydantic models:
    - resolve on BaseParams with typed fields.
"""

from typing import Any

from pydantic import ConfigDict, Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.scenarios.domain_model.roles import AdminRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# UserInfo subclass for nested structure tests
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """UserInfo subclass with dict field for nested navigation tests."""
    model_config = ConfigDict(frozen=True)
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Helper pydantic model with varied field types
# ═════════════════════════════════════════════════════════════════════════════


class TypedParams(BaseParams):
    """
    Params with mixed field types for resolve tests.
    """
    int_val: int = Field(default=42, description="Integer")
    float_val: float = Field(default=3.14, description="Float")
    str_val: str = Field(default="hello", description="String")
    bool_val: bool = Field(default=True, description="Boolean")
    none_val: str | None = Field(default=None, description="Optional string")
    list_val: list = Field(default_factory=lambda: [1, 2, 3], description="List")
    dict_val: dict = Field(default_factory=lambda: {"a": 1, "b": 2}, description="Dict")


# ═════════════════════════════════════════════════════════════════════════════
# Strings
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveStrings:
    """resolve for string values."""

    def test_regular_string(self) -> None:
        """Normal string returned unchanged."""
        user = UserInfo(user_id="test_user")
        result = user.resolve("user_id")
        assert result == "test_user"
        assert isinstance(result, str)

    def test_empty_string_is_valid_value(self) -> None:
        """Empty string "" is valid, not a missing field."""
        user = UserInfo(user_id="")
        result = user.resolve("user_id")
        assert result == ""
        assert isinstance(result, str)


# ═════════════════════════════════════════════════════════════════════════════
# Numbers
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNumbers:
    """resolve for int and float."""

    def test_int_value(self) -> None:
        """resolve returns int without coercion."""
        params = TypedParams()
        result = params.resolve("int_val")
        assert result == 42
        assert isinstance(result, int)

    def test_float_value(self) -> None:
        """resolve returns float without coercion."""
        params = TypedParams()
        result = params.resolve("float_val")
        assert result == 3.14
        assert isinstance(result, float)

    def test_zero_int_is_valid_value(self) -> None:
        """Zero 0 is valid, not missing."""
        state = BaseState(count=0)
        result = state.resolve("count")
        assert result == 0
        assert isinstance(result, int)

    def test_zero_float_is_valid_value(self) -> None:
        """Float zero 0.0 is valid."""
        state = BaseState(total=0.0)
        result = state.resolve("total")
        assert result == 0.0
        assert isinstance(result, float)


# ═════════════════════════════════════════════════════════════════════════════
# Booleans
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveBooleans:
    """resolve for True and False."""

    def test_true_value(self) -> None:
        """resolve returns True unchanged."""
        params = TypedParams()
        result = params.resolve("bool_val")
        assert result is True

    def test_false_is_valid_value(self) -> None:
        """False is valid, not missing."""
        state = BaseState(active=False)
        result = state.resolve("active")
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNone:
    """resolve when field exists with None."""

    def test_none_field_value(self) -> None:
        """Field None — resolve returns None."""
        params = TypedParams()
        result = params.resolve("none_val")
        assert result is None

    def test_none_in_state(self) -> None:
        """None in BaseState — resolve returns None."""
        state = BaseState(result=None)
        result = state.resolve("result")
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Collections: list and dict
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveCollections:
    """resolve for list and dict."""

    def test_list_value(self) -> None:
        """resolve returns roles tuple whole."""
        user = UserInfo(roles=(AdminRole, UserRole))
        result = user.resolve("roles")
        assert result == (AdminRole, UserRole)
        assert isinstance(result, tuple)

    def test_empty_list_is_valid_value(self) -> None:
        """Empty roles tuple is valid."""
        user = UserInfo(roles=())
        result = user.resolve("roles")
        assert result == ()
        assert isinstance(result, tuple)

    def test_dict_value(self) -> None:
        """resolve returns dict whole."""
        params = TypedParams()
        result = params.resolve("dict_val")
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)

    def test_empty_dict_is_valid_value(self) -> None:
        """Empty dict {} is valid."""
        user = _ExtendedUserInfo(settings={})
        result = user.resolve("settings")
        assert result == {}
        assert isinstance(result, dict)

    def test_list_from_pydantic(self) -> None:
        """resolve on pydantic model returns list from Field(default_factory=...)."""
        params = TypedParams()
        result = params.resolve("list_val")
        assert result == [1, 2, 3]
        assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════════════
# Nested mixed structures
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveMixedNested:
    """resolve through nested structures with mixed types."""

    def test_nested_dict_with_various_types(self) -> None:
        """
        Dict inside subclass holds mixed-type values.
        resolve extracts each type from nested structure.
        """
        # Arrange
        user = _ExtendedUserInfo(
            user_id="42",
            roles=(AdminRole,),
            settings={
                "notifications": {
                    "email": True,
                    "count": 5,
                    "channels": ["sms", "push"],
                },
            },
        )
        ctx = Context(user=user)

        # Act & Assert
        assert ctx.resolve("user.settings.notifications.email") is True
        assert ctx.resolve("user.settings.notifications.count") == 5
        channels = ctx.resolve("user.settings.notifications.channels")
        assert channels == ["sms", "push"]
        assert isinstance(channels, list)

    def test_dict_value_from_extended_field(self) -> None:
        """
        resolve to intermediate level returns whole dict.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"theme": "dark", "lang": "en"})
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.settings")

        # Assert
        assert result == {"theme": "dark", "lang": "en"}
        assert isinstance(result, dict)
