# tests/model/test_frozen_state.py
"""
Tests for frozen semantics of BaseState.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures BaseState is fully immutable after creation: attribute assignment and
deletion are forbidden. The only way to “change” state is to create a new
instance.

BaseState is a pydantic model with frozen=True and extra="allow". Built via
kwargs: BaseState(total=100, user="agent"). Dynamic fields are allowed at
construction (extra="allow") but writes after creation are forbidden
(frozen=True).

Also verifies reads: dict-like access, resolve, keys, values, items, to_dict,
repr.
"""

import pytest
from pydantic import ValidationError

from action_machine.model.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Creation and reads
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateCreation:
    """Creation and reads from BaseState."""

    def test_create_empty(self) -> None:
        """Empty BaseState creates without error and has no fields."""
        # Arrange & Act
        state = BaseState()

        # Assert — empty state
        assert state.to_dict() == {}
        assert state.keys() == []

    def test_create_with_data(self) -> None:
        """BaseState accepts kwargs; each key becomes a field."""
        # Arrange
        data = {"total": 1500, "user": "agent", "active": True}

        # Act
        state = BaseState(**data)

        # Assert — all data reachable via dict interface
        assert state["total"] == 1500
        assert state["user"] == "agent"
        assert state["active"] is True

    def test_getitem_access(self) -> None:
        """Dict-like access via brackets."""
        # Arrange
        state = BaseState(amount=42.5)

        # Act & Assert
        assert state["amount"] == 42.5

    def test_getitem_missing_key_raises(self) -> None:
        """Missing key raises KeyError."""
        # Arrange
        state = BaseState(exists=True)

        # Act & Assert — key missing
        with pytest.raises(KeyError):
            _ = state["missing"]

    def test_get_with_default(self) -> None:
        """get() returns default for missing key."""
        # Arrange
        state = BaseState(key="value")

        # Act & Assert
        assert state.get("key") == "value"
        assert state.get("missing") is None
        assert state.get("missing", "fallback") == "fallback"

    def test_contains(self) -> None:
        """``in`` checks key presence."""
        # Arrange
        state = BaseState(present=1)

        # Act & Assert
        assert "present" in state
        assert "absent" not in state

    def test_keys_values_items(self) -> None:
        """keys, values, items return correct data."""
        # Arrange
        state = BaseState(a=1, b=2)

        # Act
        keys = state.keys()
        values = state.values()
        items = state.items()

        # Assert
        assert set(keys) == {"a", "b"}
        assert set(values) == {1, 2}
        assert set(items) == {("a", 1), ("b", 2)}

    def test_to_dict(self) -> None:
        """to_dict() returns a dict of all fields."""
        # Arrange
        state = BaseState(x=10, y=20)

        # Act
        result = state.to_dict()

        # Assert — plain dict
        assert result == {"x": 10, "y": 20}
        assert isinstance(result, dict)

    def test_to_dict_matches_model_dump(self) -> None:
        """to_dict() matches model_dump()."""
        # Arrange
        state = BaseState(a=1, b="two")

        # Act & Assert
        assert state.to_dict() == state.model_dump()

    def test_resolve(self) -> None:
        """resolve() works for flat keys."""
        # Arrange
        state = BaseState(total=500)

        # Act & Assert
        assert state.resolve("total") == 500
        assert state.resolve("missing") is None

        # Separate instance for default check
        fresh_state = BaseState(total=500)
        assert fresh_state.resolve("missing", default="default") == "default"

    def test_repr(self) -> None:
        """repr() shows content as BaseState(key=value)."""
        # Arrange
        state = BaseState(count=3)

        # Act
        result = repr(state)

        # Assert
        assert "BaseState" in result
        assert "count=3" in result


# ═════════════════════════════════════════════════════════════════════════════
# Frozen semantics: writes forbidden
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateFrozen:
    """Immutability of BaseState after creation."""

    def test_setattr_raises(self) -> None:
        """Attribute assignment forbidden."""
        # Arrange
        state = BaseState(value=1)

        # Act & Assert
        with pytest.raises(ValidationError):
            state.value = 2

    def test_setattr_new_key_raises(self) -> None:
        """New attribute forbidden."""
        # Arrange
        state = BaseState()

        # Act & Assert
        with pytest.raises(ValidationError):
            state.new_key = "value"

    def test_delattr_raises(self) -> None:
        """Attribute deletion forbidden."""
        # Arrange
        state = BaseState(to_delete="value")

        # Act & Assert
        with pytest.raises(ValidationError):
            del state.to_delete

    def test_no_setitem(self) -> None:
        """Dict-like write via [] forbidden (no __setitem__)."""
        # Arrange
        state = BaseState(key="old")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            state["key"] = "new"

    def test_no_delitem(self) -> None:
        """Dict-like del via [] forbidden."""
        # Arrange
        state = BaseState(key="value")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            del state["key"]

    def test_no_write_method(self) -> None:
        """write() does not exist."""
        # Arrange
        state = BaseState()

        # Act & Assert
        assert not hasattr(state, "write")

    def test_no_update_method(self) -> None:
        """update() does not exist."""
        # Arrange
        state = BaseState()

        # Act & Assert
        assert not hasattr(state, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Update pattern — new instance
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateImmutableUpdate:
    """Updates by constructing a new instance."""

    def test_merge_creates_new_state(self) -> None:
        """Merging two states yields a new object; old unchanged."""
        # Arrange
        old_state = BaseState(total=100)
        new_data = {"discount": 10}

        # Act — pattern used by the machine each pipeline step
        new_state = BaseState(**{**old_state.to_dict(), **new_data})

        # Assert — new state has both fields
        assert new_state["total"] == 100
        assert new_state["discount"] == 10

        # Assert — old state unchanged
        assert old_state.to_dict() == {"total": 100}
        assert "discount" not in old_state

    def test_override_creates_new_state(self) -> None:
        """Overwriting a field yields a new object with updated value."""
        # Arrange
        original = BaseState(status="pending")

        # Act
        updated = BaseState(**{**original.to_dict(), "status": "completed"})

        # Assert
        assert updated["status"] == "completed"
        assert original["status"] == "pending"

    def test_original_and_copy_are_independent(self) -> None:
        """Two BaseState instances from same data are independent objects."""
        # Arrange
        data = {"count": 0}
        state_a = BaseState(**data)
        state_b = BaseState(**data)

        # Act & Assert — different objects, same data
        assert state_a is not state_b
        assert state_a.to_dict() == state_b.to_dict()
