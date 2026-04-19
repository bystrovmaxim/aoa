# tests/integration/test_navigation_consistency.py
"""Integration test: navigation consistency between BaseSchema.resolve()
and VariableSubstitutor.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks what BaseSchema.resolve() and VariableSubstitutor give
same results for the same path on the same object.

Both components delegate navigation to a single DotPathNavigator [1].
This test ensures that desync between them is not possible
with future changes - it was precisely this desynchronization that led
to error #1 when resolve() used None as an absence marker [2],
and VariableSubstitutor is _SENTINEL [4].

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

String value:
    resolve("user.user_id") == "test_user"
    substitute("{%context.user.user_id}") contains "test_user"

Numeric value:
    resolve("nested.count") == 42
    substitute("{%state.nested.count}") contains "42"

None value (field exists):
    resolve("optional_field") is None
    substitute("{%state.optional_field}") contains "None" (does not fall)

Missing path:
    resolve("missing") returns default
    substitute("{%context.missing}") → LogTemplateError

Nested dict:
    resolve("data.key") == "value"
    substitute("{%var.data.key}") contains "value"

Falsy values (0, False, ""):
    resolve returns a false value, not default
    substitute contains a string representation of the falsy value"""

from typing import Any

import pytest
from pydantic import ConfigDict, Field

from action_machine.context.context import Context
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import LogTemplateError
from action_machine.testing.stubs import ContextStub

# ─────────────────────────────────────────────────────────────────────────────
#Auxiliary models
# ─────────────────────────────────────────────────────────────────────────────

class _NullableSchema(BaseSchema):
    """A scheme with nullable fields for testing None values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Name")
    optional_field: str | None = Field(default=None, description="Optional field")


class _FalsySchema(BaseSchema):
    """Scheme with falsy values ​​for testing 0, False, ''."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    zero_int: int = Field(description="Zero")
    zero_float: float = Field(description="Fractional zero")
    false_bool: bool = Field(description="Lie")
    empty_str: str = Field(description="Empty string")


# ─────────────────────────────────────────────────────────────────────────────
#General fittings
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sub() -> VariableSubstitutor:
    """A fresh instance of VariableSubstitutor."""
    return VariableSubstitutor()


@pytest.fixture()
def scope() -> LogScope:
    """Minimum LogScope."""
    return LogScope(machine="M", mode="test", action="A", aspect="a", nest_level=0)


@pytest.fixture()
def state() -> BaseState:
    """Empty BaseState."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Empty BaseParams."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
#String values ​​- resolve and substitutor give the same result
# ═════════════════════════════════════════════════════════════════════════════

class TestStringValueConsistency:
    """String value: resolve() and substitutor are consistent."""

    def test_context_user_id(self, sub, scope, state, params) -> None:
        """resolve("user.user_id") and {%context.user.user_id} - one result."""
        # Arrange
        ctx = ContextStub()

        #Act - via resolve
        result_resolve = ctx.resolve("user.user_id")

        #Act - via substitutor
        result_sub = sub.substitute(
            "{%context.user.user_id}", {}, scope, ctx, state, params
        )

        #Assert - both return the same value
        assert result_resolve == "test_user"
        assert result_resolve in result_sub

    def test_nested_schema_field(self, sub, scope, state, params) -> None:
        """Nested field via BaseSchema - consistency."""
        # Arrange
        ctx = ContextStub()

        # Act
        result_resolve = ctx.resolve("user.roles")
        result_sub = sub.substitute(
            "{%context.user.roles}", {}, scope, ctx, state, params
        )

        # Assert
        assert result_resolve is not None
        assert str(result_resolve) in result_sub


# ═════════════════════════════════════════════════════════════════════════════
#Numeric values
# ═════════════════════════════════════════════════════════════════════════════

class TestNumericValueConsistency:
    """Numeric value: resolve() and substitutor are consistent."""

    def test_state_numeric_field(self, sub, scope, ctx_stub, params) -> None:
        """A numeric field in state gives the same result."""
        # Arrange
        st = BaseState(count=42)

        # Act
        result_resolve = st.resolve("count")
        result_sub = sub.substitute("{%state.count}", {}, scope, ctx_stub, st, params)

        # Assert
        assert result_resolve == 42
        assert "42" in result_sub

    @pytest.fixture()
    def ctx_stub(self) -> Context:
        return ContextStub()


# ═════════════════════════════════════════════════════════════════════════════
#None values ​​are a key scenario (error #1)
# ═════════════════════════════════════════════════════════════════════════════

class TestNoneValueConsistency:
    """None as field value: resolve() and substitutor are consistent [7]."""

    def test_none_field_resolve_returns_none(self) -> None:
        """resolve() for a field with None returns None, not default."""
        # Arrange
        schema = _NullableSchema(name="Alice", optional_field=None)

        # Act
        result = schema.resolve("optional_field", default="fallback")

        #Assert - None is a valid value, not absence
        assert result is None

    def test_none_field_substitutor_returns_none_string(
        self, sub, scope, state, params
    ) -> None:
        """substitutor for a field with None outputs 'None', does not crash."""
        # Arrange
        st = BaseState(optional_field=None)

        # Act
        result = sub.substitute(
            "{%state.optional_field}", {}, scope, ContextStub(), st, params
        )

        #Assert - substitutor converts None to the string "None"
        assert "None" in result

    def test_none_consistency_between_resolve_and_substitutor(
        self, sub, scope, params
    ) -> None:
        """resolve() returns None, substitutor outputs str(None) - agreed."""
        # Arrange
        st = BaseState(value=None)

        # Act
        result_resolve = st.resolve("value")
        result_sub = sub.substitute(
            "{%state.value}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve is None
        assert str(result_resolve) in result_sub


# ═════════════════════════════════════════════════════════════════════════════
#Missing path - resolve returns default, substitutor throws an error
# ═════════════════════════════════════════════════════════════════════════════

class TestMissingPathBehavior:
    """Missing path: different behavior - and this is correct."""

    def test_resolve_returns_default_for_missing(self) -> None:
        """resolve() for a non-existent path returns default [7]."""
        # Arrange
        ctx = ContextStub()

        # Act
        result = ctx.resolve("user.nonexistent", default="MISSING")

        # Assert
        assert result == "MISSING"

    def test_substitutor_raises_for_missing(self, sub, scope, state, params) -> None:
        """substitutor for a non-existent path throws LogTemplateError [4]."""
        # Arrange
        ctx = ContextStub()

        #Act & Assert - strict error policy
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute(
                "{%context.user.nonexistent}", {}, scope, ctx, state, params
            )


# ═════════════════════════════════════════════════════════════════════════════
#Nested dict - navigation via DotPathNavigator
# ═════════════════════════════════════════════════════════════════════════════

class TestNestedDictConsistency:
    """Nested dict: resolve() and substitutor through one navigator."""

    def test_var_nested_dict(self, sub, scope, state, params) -> None:
        """Three-level dict - both ways give the same result."""
        # Arrange
        data: dict[str, Any] = {"a": {"b": {"c": "deep"}}}

        #Act - via substitutor (var namespace - dict)
        result_sub = sub.substitute(
            "{%var.a.b.c}", data, scope, ContextStub(), state, params
        )

        # Assert
        assert "deep" in result_sub

    def test_state_with_nested_dict(self, sub, scope, params) -> None:
        """BaseState with nested dict - resolve and substitutor are consistent."""
        # Arrange
        st = BaseState(nested={"key": "value"})

        # Act
        result_resolve = st.resolve("nested.key")
        result_sub = sub.substitute(
            "{%state.nested.key}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == "value"
        assert "value" in result_sub


# ═════════════════════════════════════════════════════════════════════════════
#Falsy values ​​- 0, False, "" are not replaced by default
# ═════════════════════════════════════════════════════════════════════════════

class TestFalsyValueConsistency:
    """Falsy values: resolve() and substitutor are not confused with absence [8]."""

    def test_zero_int(self, sub, scope, params) -> None:
        """A value of 0 is valid, not absent."""
        # Arrange
        st = BaseState(count=0)

        # Act
        result_resolve = st.resolve("count", default="MISSING")
        result_sub = sub.substitute(
            "{%state.count}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == 0
        assert "0" in result_sub

    def test_false_bool(self, sub, scope, params) -> None:
        """The value False is valid, not absent."""
        # Arrange
        st = BaseState(flag=False)

        # Act
        result_resolve = st.resolve("flag", default="MISSING")
        result_sub = sub.substitute(
            "{%state.flag}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve is False
        assert "False" in result_sub

    def test_empty_string(self, sub, scope, params) -> None:
        """The value '' is valid, not absent."""
        # Arrange
        st = BaseState(label="")

        # Act
        result_resolve = st.resolve("label", default="MISSING")
        result_sub = sub.substitute(
            "{%state.label}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == ""
        assert result_sub is not None


# ═════════════════════════════════════════════════════════════════════════════
#LogScope - navigation via duck-typed __getitem__
# ═════════════════════════════════════════════════════════════════════════════

class TestLogScopeConsistency:
    """LogScope: substitutor navigates correctly via __getitem__ [3]."""

    def test_scope_field_via_substitutor(self, sub, state, params) -> None:
        """The scope field is accessible via {%scope.action}."""
        # Arrange
        sc = LogScope(
            machine="TestMachine", mode="test",
            action="MyAction", aspect="my_aspect", nest_level=0,
        )

        # Act
        result = sub.substitute(
            "{%scope.action}", {}, sc, ContextStub(), state, params
        )

        # Assert
        assert "MyAction" in result

    def test_scope_field_via_getitem(self) -> None:
        """LogScope["action"] returns the same value."""
        # Arrange
        sc = LogScope(action="MyAction")

        # Act & Assert
        assert sc["action"] == "MyAction"
        assert sc["action"] == "MyAction"
