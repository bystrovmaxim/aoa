# tests/model/test_resolve_flat.py
"""
Tests for BaseSchema.resolve() on flat fields (no nesting).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

resolve(dotpath, default) is the main navigation mechanism for logging templates
in ActionMachine. Templates like {%context.user.user_id}, {%state.total},
{%params.amount} are resolved via resolve().

This file covers the simplest case: flat fields with no nesting.
resolve("user_id") for a single path segment is equivalent to __getitem__("user_id")
with KeyError handled → return default.

More complex cases (nested objects, dicts, mixed types) live in
test_base_schema_resolve.py.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Basic access:
    - String field — resolve returns str.
    - Numeric field — resolve returns int or float.
    - List field — resolve returns the whole list.
    - Field with default — default ignored when key exists.

None as value:
    - Field None — resolve returns None, not default.
    - None with default — default NOT applied when field exists.

Different object types:
    - UserInfo (BaseSchema, frozen, forbid) — flat fields.
    - BaseState (BaseSchema, frozen, allow) — dynamic extra fields.
    - BaseParams (BaseSchema, frozen, forbid) — declared pydantic fields.

Falsy values:
    - Empty string "" — valid value, not “missing”.
    - Zero 0 — valid value, not “missing”.
    - False — valid value, not “missing”.
"""

from pydantic import Field

from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState
from tests.action_machine.scenarios.domain_model.roles import AdminRole, AgentRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Basic flat field access
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatBasic:
    """Basic flat field access via resolve()."""

    def test_resolve_string_field(self) -> None:
        """
        resolve("user_id") returns the string field value.

        UserInfo subclasses BaseSchema. resolve splits "user_id" by dots
        → ["user_id"], calls __getitem__("user_id") → getattr(self, "user_id").
        """
        # Arrange
        user = UserInfo(user_id="agent_007", roles=(AgentRole,))

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_list_field(self) -> None:
        """
        resolve("roles") returns the full role types tuple.

        resolve does not index tuple elements (roles.0).
        Get the tuple first, then index in Python.
        """
        # Arrange
        user = UserInfo(user_id="42", roles=(AdminRole, UserRole))

        # Act
        result = user.resolve("roles")

        # Assert
        assert result == (AdminRole, UserRole)
        assert isinstance(result, tuple)

    def test_resolve_existing_field_ignores_default(self) -> None:
        """
        For an existing field, default is ignored.

        resolve("user_id", default="N/A") returns the real value.
        Default applies only when the path is missing.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("user_id", default="N/A")

        # Assert
        assert result == "42"


# ═════════════════════════════════════════════════════════════════════════════
# None as field value
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatNone:
    """None as field value vs missing field."""

    def test_resolve_none_value(self) -> None:
        """
        Field with value None — resolve returns None.

        UserInfo(user_id=None) — user_id exists but is None.
        resolve returns that value as-is, not default.
        """
        # Arrange
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result is None

    def test_resolve_none_value_ignores_default(self) -> None:
        """
        None with default — default NOT applied.

        Unlike missing field: if field exists and is None, default is skipped.
        Default applies only when __getitem__ raises KeyError.
        """
        # Arrange
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Different BaseSchema subclasses
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatDifferentObjects:
    """resolve() behaves consistently across BaseSchema subclasses."""

    def test_resolve_on_base_state(self) -> None:
        """
        resolve() on BaseState — dynamic extra fields.

        BaseState uses extra="allow". Kwargs at construction are visible
        via __getitem__ and resolve like declared fields.
        """
        # Arrange
        state = BaseState(txn_id="TXN-001", total=1500.0)

        # Act
        txn_id = state.resolve("txn_id")
        total = state.resolve("total")

        # Assert
        assert txn_id == "TXN-001"
        assert total == 1500.0

    def test_resolve_on_pydantic_params(self) -> None:
        """
        resolve() on pydantic BaseParams — declared model fields.

        BaseParams subclasses BaseSchema. resolve uses __getitem__ → getattr
        like other BaseSchema types.
        """
        # Arrange
        class TestParams(BaseParams):
            name: str = Field(description="Name")
            count: int = Field(description="Count")

        params = TestParams(name="test", count=5)

        # Act
        name = params.resolve("name")
        count = params.resolve("count")

        # Assert
        assert name == "test"
        assert count == 5

    def test_resolve_on_user_info(self) -> None:
        """
        resolve() on UserInfo — frozen BaseSchema with two fields.

        UserInfo has user_id and roles. No extra — extend via subclassing.
        """
        # Arrange
        user = UserInfo(
            user_id="test_user",
            roles=(AdminRole, ManagerRole),
        )

        # Act
        user_id = user.resolve("user_id")
        roles = user.resolve("roles")

        # Assert
        assert user_id == "test_user"
        assert roles == (AdminRole, ManagerRole)

    def test_resolve_empty_string_field(self) -> None:
        """
        Empty string "" is a valid value, not “missing”.
        resolve returns "", not default.
        """
        # Arrange
        user = UserInfo(user_id="")

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result == ""
        assert isinstance(result, str)

    def test_resolve_zero_value(self) -> None:
        """
        Zero 0 is a valid value, not “missing”.
        resolve returns 0, not default. Zero is falsy in Python,
        but resolve distinguishes “field found with 0” from “missing → default”.
        """
        # Arrange
        state = BaseState(count=0)

        # Act
        result = state.resolve("count")

        # Assert
        assert result == 0
        assert isinstance(result, int)

    def test_resolve_false_value(self) -> None:
        """
        False is a valid value, not “missing”.
        Same idea as zero: falsy but field exists.
        """
        # Arrange
        state = BaseState(active=False)

        # Act
        result = state.resolve("active")

        # Assert
        assert result is False
