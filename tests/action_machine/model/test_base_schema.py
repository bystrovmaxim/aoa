# tests/model/test_base_schema.py
"""
Tests for BaseSchema — base pydantic schema with dict-like field access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseSchema subclasses pydantic.BaseModel and adds a dict-like interface:
__getitem__, __contains__, get, keys, values, items.

Framework data structures inherit BaseSchema:
- BaseParams — action inputs (frozen, forbid).
- BaseResult — action output (frozen, forbid).
- BaseState — pipeline state (frozen, allow).
- Context, UserInfo, RequestInfo, RuntimeInfo — execution context.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Flat access:
    - keys() returns declared model field names.
    - values() returns declared field values.
    - items() returns (key, value) pairs.
    - __getitem__ returns value; KeyError when missing.
    - __contains__ checks field presence.
    - get() returns value or default.

Extra fields (BaseState with extra="allow"):
    - keys/values/items include dynamic extra fields.
    - __getitem__ works for extra fields.
    - __contains__ finds extra fields.

Strict models (extra="forbid"):
    - Empty model yields empty keys/values/items.
    - Model with declared fields returns only those.

Pydantic compatibility:
    - model_dump() serializes all fields.
    - Frozen models forbid writes.
"""

import pytest
from pydantic import ConfigDict, Field, ValidationError

from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_schema import BaseSchema
from aoa.action_machine.model.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Helper classes for tests
# ═════════════════════════════════════════════════════════════════════════════


class SimpleSchema(BaseSchema):
    """
    Simple schema with a few fields for testing.
    Not frozen — allows writes for basic operation checks.
    """

    model_config = ConfigDict(frozen=False)

    name: str = ""
    value: int = 0
    active: bool = False


class FrozenSchema(BaseSchema):
    """Frozen schema for immutability checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: float = 0.0


# ═════════════════════════════════════════════════════════════════════════════
# Flat access: keys, values, items
# ═════════════════════════════════════════════════════════════════════════════


class TestKeysValuesItems:
    """keys(), values(), items() iterate schema fields."""

    def test_keys_returns_declared_fields(self) -> None:
        """
        keys() returns declared model field names.

        BaseSchema uses model_fields.keys() for pydantic models.
        Internal pydantic attrs are not included.
        """
        # Arrange
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        keys = obj.keys()

        # Assert
        assert sorted(keys) == ["active", "name", "value"]

    def test_values_returns_field_values(self) -> None:
        """
        values() returns declared field values.
        Order matches keys().
        """
        # Arrange
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        values = obj.values()

        # Assert
        assert set(values) == {"test", 42, True}

    def test_items_returns_pairs(self) -> None:
        """
        items() returns (key, value) pairs for all fields.
        """
        # Arrange
        obj = SimpleSchema(name="Alice", value=7, active=False)

        # Act
        items = dict(obj.items())

        # Assert
        assert items == {"name": "Alice", "value": 7, "active": False}

    def test_keys_for_empty_pydantic_model(self) -> None:
        """
        keys() for empty pydantic model with no fields returns empty list.
        """
        # Arrange
        result = BaseResult()

        # Act
        keys = result.keys()

        # Assert
        assert keys == []

    def test_keys_includes_extra_fields_for_state(self) -> None:
        """
        keys() for BaseState (extra="allow") includes dynamic extra
        fields passed at construction via kwargs.
        """
        # Arrange
        state = BaseState(total=1500, user="agent")

        # Act
        keys = state.keys()

        # Assert
        assert sorted(keys) == ["total", "user"]

    def test_values_includes_extra_for_state(self) -> None:
        """
        values() for BaseState includes extra field values.
        """
        # Arrange
        state = BaseState(total=1500, user="agent")

        # Act
        values = state.values()

        # Assert
        assert set(values) == {1500, "agent"}

    def test_items_includes_extra_for_state(self) -> None:
        """
        items() for BaseState includes extra field pairs.
        """
        # Arrange
        state = BaseState(count=42, flag=True)

        # Act
        items = dict(state.items())

        # Assert
        assert items == {"count": 42, "flag": True}


# ═════════════════════════════════════════════════════════════════════════════
# Flat access: __getitem__, __contains__, get
# ═════════════════════════════════════════════════════════════════════════════


class TestDictAccess:
    """__getitem__, __contains__, get() — dict-like access."""

    def test_getitem_returns_value(self) -> None:
        """obj["key"] returns field value."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act
        result = obj["name"]

        # Assert
        assert result == "Alice"

    def test_getitem_missing_raises_key_error(self) -> None:
        """obj["missing"] raises KeyError."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        with pytest.raises(KeyError):
            _ = obj["missing"]

    def test_getitem_on_state_extra_field(self) -> None:
        """__getitem__ works for BaseState extra fields."""
        # Arrange
        state = BaseState(txn_id="TXN-001")

        # Act
        result = state["txn_id"]

        # Assert
        assert result == "TXN-001"

    def test_contains_existing_key(self) -> None:
        """"key" in obj is True when field exists."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        assert "name" in obj

    def test_contains_missing_key(self) -> None:
        """"missing" in obj is False when field absent."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        assert "missing" not in obj

    def test_contains_extra_field_in_state(self) -> None:
        """__contains__ finds BaseState extra fields."""
        # Arrange
        state = BaseState(total=100)

        # Act & Assert
        assert "total" in state
        assert "missing" not in state

    def test_get_existing_key(self) -> None:
        """obj.get("key") returns existing field value."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("value")

        # Assert
        assert result == 42

    def test_get_missing_key_returns_default(self) -> None:
        """obj.get("missing", default) returns default."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("missing", "fallback")

        # Assert
        assert result == "fallback"

    def test_get_missing_key_without_default_returns_none(self) -> None:
        """obj.get("missing") without default returns None."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("missing")

        # Assert
        assert result is None

    def test_getitem_on_pydantic_result(self) -> None:
        """__getitem__ on pydantic BaseResult with declared field."""

        # Arrange
        class _TestResult(BaseResult):
            metric: float = Field(description="Test metric")

        result = _TestResult(metric=99.5)

        # Act
        value = result["metric"]

        # Assert
        assert value == 99.5

        # Act & Assert — missing field
        with pytest.raises(KeyError):
            _ = result["nonexistent"]


# ═════════════════════════════════════════════════════════════════════════════
# Frozen semantics
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozenSemantics:
    """Immutability of frozen schemas."""

    def test_frozen_schema_rejects_write(self) -> None:
        """Frozen schema forbids attribute writes after creation."""
        # Arrange
        obj = FrozenSchema(metric=3.14)

        # Act & Assert — pydantic ValidationError for frozen models
        with pytest.raises(ValidationError):
            obj.metric = 0.0

    def test_state_is_frozen(self) -> None:
        """BaseState (frozen=True) forbids writes after creation."""
        # Arrange
        state = BaseState(total=100)

        # Act & Assert
        with pytest.raises(ValidationError):
            state.total = 200  # type: ignore[misc]

    def test_result_is_frozen(self) -> None:
        """BaseResult (frozen=True) forbids writes after creation."""

        class _TestResult(BaseResult):
            status: str = Field(description="Status")

        # Arrange
        result = _TestResult(status="ok")

        # Act & Assert
        with pytest.raises(ValidationError):
            result.status = "fail"  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Serialization
# ═════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Serialization via model_dump()."""

    def test_model_dump_declared_fields(self) -> None:
        """model_dump() returns dict of declared fields."""
        # Arrange
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        dumped = obj.model_dump()

        # Assert
        assert dumped == {"name": "test", "value": 42, "active": True}

    def test_model_dump_state_extra_fields(self) -> None:
        """model_dump() for BaseState includes extra fields."""
        # Arrange
        state = BaseState(total=1500, user="agent")

        # Act
        dumped = state.model_dump()

        # Assert
        assert dumped == {"total": 1500, "user": "agent"}

    def test_state_to_dict(self) -> None:
        """BaseState.to_dict() matches model_dump()."""
        # Arrange
        state = BaseState(a=1, b="two")

        # Act
        result = state.to_dict()

        # Assert
        assert result == {"a": 1, "b": "two"}
        assert result == state.model_dump()

    def test_empty_state_to_dict(self) -> None:
        """Empty BaseState.to_dict() returns {}."""
        # Arrange
        state = BaseState()

        # Act
        result = state.to_dict()

        # Assert
        assert result == {}
