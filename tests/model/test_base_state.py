# tests/model/test_base_state.py
"""
Tests for BaseState — frozen aspect pipeline state.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseState is a frozen pydantic model (subclass of BaseSchema) with extra="allow"
holding accumulated data between aspect pipeline steps. Each regular aspect
returns a dict of new fields; the machine validates them with checkers and
builds a NEW BaseState via kwargs:

    new_state = BaseState(**{**old_state.to_dict(), **aspect_result})

Aspects receive state read-only — mutation is impossible after creation
(frozen=True).

BaseState inherits BaseSchema (dict-like reads, resolve by dot-path).
Write methods (__setitem__, __delitem__, write, update) are absent.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Construction:
    - Via kwargs — keys become extra fields.
    - Empty — initial state before the first aspect.

Reads (BaseSchema):
    - __getitem__, __contains__, get, keys, values, items.
    - resolve for flat fields and default for missing paths.

Immutability (frozen=True):
    - setattr forbidden (frozen).
    - __setitem__ absent.
    - __delitem__ absent.
    - write and update absent.

Serialization:
    - to_dict() / model_dump() return all fields.
    - repr() includes class name and fields.
"""

import pytest
from pydantic import ValidationError

from action_machine.model.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Construction
# ═════════════════════════════════════════════════════════════════════════════


class TestCreation:
    """BaseState via kwargs and empty."""

    def test_create_from_dict(self) -> None:
        """
        Dict-like data at construction — each key becomes an extra field.

        Machine builds BaseState by unpacking kwargs:
        BaseState(**{**old_state.to_dict(), **new_dict}).
        """
        # Arrange — data a regular aspect might return
        initial = {"txn_id": "TXN-001", "total": 1500.0}

        # Act — state from kwargs
        state = BaseState(**initial)

        # Assert — each key is an extra field (dot and bracket access)
        assert state.txn_id == "TXN-001"
        assert state.total == 1500.0

    def test_create_empty(self) -> None:
        """
        Empty state — before the first regular aspect.
        Machine creates BaseState() before iterating regular aspects.
        """
        # Arrange & Act — initial empty state
        state = BaseState()

        # Assert — empty dict
        assert state.to_dict() == {}

    def test_create_with_kwargs(self) -> None:
        """
        BaseState accepts kwargs directly.
        """
        # Arrange & Act
        state = BaseState(a=1, b="two", c=True)

        # Assert
        assert state["a"] == 1
        assert state["b"] == "two"
        assert state["c"] is True


# ═════════════════════════════════════════════════════════════════════════════
# Reads via BaseSchema
# ═════════════════════════════════════════════════════════════════════════════


class TestReadAccess:
    """Dict-like reads on BaseState via BaseSchema."""

    def test_getitem_returns_value(self) -> None:
        """
        state["key"] — primary read path in aspects.
        """
        # Arrange
        state = BaseState(amount=500)

        # Act
        result = state["amount"]

        # Assert
        assert result == 500

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        Missing key → KeyError.
        """
        # Arrange
        state = BaseState()

        # Act & Assert
        with pytest.raises(KeyError):
            _ = state["missing"]

    def test_contains_checks_key_existence(self) -> None:
        """
        ``in`` checks key presence.
        """
        # Arrange
        state = BaseState(total=100)

        # Act & Assert
        assert "total" in state
        assert "missing" not in state

    def test_get_returns_value_or_default(self) -> None:
        """
        state.get("key", default) — safe read without KeyError.
        """
        # Arrange
        state = BaseState(total=100)

        # Act & Assert — existing key
        assert state.get("total") == 100
        # missing with default
        assert state.get("missing", "fallback") == "fallback"
        # missing without default → None
        assert state.get("missing") is None

    def test_keys_values_items(self) -> None:
        """
        keys(), values(), items() iterate state contents.
        """
        # Arrange
        state = BaseState(a=1, b=2)

        # Act
        keys = state.keys()
        values = state.values()
        items = state.items()

        # Assert
        assert sorted(keys) == ["a", "b"]
        assert sorted(values) == [1, 2]
        assert sorted(items) == [("a", 1), ("b", 2)]

    def test_resolve_flat_field(self) -> None:
        """
        resolve("key") — flat field access.
        Used in log templates: {%state.total}
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = state.resolve("total")

        # Assert
        assert result == 1500

    def test_resolve_missing_returns_none(self) -> None:
        """
        resolve("missing") without default returns None.
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = state.resolve("missing")

        # Assert
        assert result is None

    def test_resolve_missing_with_explicit_default(self) -> None:
        """
        resolve("missing", default="N/A") returns "N/A".
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = state.resolve("missing", default="N/A")

        # Assert
        assert result == "N/A"


# ═════════════════════════════════════════════════════════════════════════════
# Immutability (frozen)
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """BaseState is immutable after creation (frozen=True)."""

    def test_setattr_raises(self) -> None:
        """
        Direct attribute write forbidden.
        pydantic frozen=True raises ValidationError.
        """
        # Arrange
        state = BaseState(value=1)

        # Act & Assert
        with pytest.raises(ValidationError):
            state.value = 2

    def test_setattr_new_key_raises(self) -> None:
        """
        New attribute forbidden.
        pydantic frozen=True raises ValidationError.
        """
        # Arrange
        state = BaseState()

        # Act & Assert
        with pytest.raises(ValidationError):
            state.new_key = "value"

    def test_delattr_raises(self) -> None:
        """
        Attribute deletion forbidden.
        pydantic frozen=True raises ValidationError on delete.
        """
        # Arrange
        state = BaseState(to_delete="value")

        # Act & Assert
        with pytest.raises(ValidationError):
            del state.to_delete

    def test_setitem_raises(self) -> None:
        """
        Dict-like write via [] not defined.
        BaseState has no __setitem__.
        """
        # Arrange
        state = BaseState(key="old")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            state["key"] = "new"

    def test_delitem_raises(self) -> None:
        """
        Dict-like del via [] not defined.
        """
        # Arrange
        state = BaseState(key="value")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            del state["key"]

    def test_write_method_missing(self) -> None:
        """write() is absent."""
        state = BaseState()
        assert not hasattr(state, "write")

    def test_update_method_missing(self) -> None:
        """update() is absent."""
        state = BaseState()
        assert not hasattr(state, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Serialization
# ═════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """BaseState serialization: to_dict(), model_dump(), repr()."""

    def test_to_dict_returns_all_fields(self) -> None:
        """
        to_dict() returns all extra fields.
        Same as model_dump(). Used for plugins (state_aspect in PluginEvent)
        and logging.
        """
        # Arrange
        state = BaseState(a=1, b=2)

        # Act
        result = state.to_dict()

        # Assert
        assert result == {"a": 1, "b": 2}

    def test_to_dict_matches_model_dump(self) -> None:
        """
        to_dict() matches model_dump().
        """
        # Arrange
        state = BaseState(total=100)
        state.resolve("total")  # resolve does not affect to_dict

        # Act
        result = state.to_dict()

        # Assert
        assert result == state.model_dump()
        assert result == {"total": 100}

    def test_repr_contains_class_name_and_fields(self) -> None:
        """
        repr() looks like "BaseState(key1=value1, key2=value2)".
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = repr(state)

        # Assert
        assert "BaseState" in result
        assert "total" in result
        assert "1500" in result

    def test_repr_empty_state(self) -> None:
        """
        repr() of empty state is "BaseState()".
        """
        # Arrange & Act
        state = BaseState()

        # Act
        result = repr(state)

        # Assert
        assert result == "BaseState()"
