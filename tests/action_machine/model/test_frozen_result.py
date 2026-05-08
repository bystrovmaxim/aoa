# tests/model/test_frozen_result.py
"""
Tests for frozen semantics of BaseResult.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures BaseResult and subclasses are fully immutable after creation: attribute
assignment, arbitrary fields, dict-like writes — all forbidden. Arbitrary
fields are forbidden (extra="forbid") [1].

Also verifies read access via BaseSchema [2] and serialization via pydantic
model_dump() / model_json_schema().
"""

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.model.base_result import BaseResult

# ═════════════════════════════════════════════════════════════════════════════
# Test subclass of BaseResult
# ═════════════════════════════════════════════════════════════════════════════

class OrderResult(BaseResult):
    """Test result with three explicitly declared fields."""
    order_id: str = Field(description="Order ID")
    status: str = Field(description="Order status")
    total: float = Field(description="Total amount", ge=0)


class EmptyResult(BaseResult):
    """Test result with no fields — smoke tests."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Creation and reads
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultCreation:
    """Creation and reads from BaseResult."""

    def test_create_with_fields(self) -> None:
        """Subclass is created with explicit fields."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        assert result.order_id == "ORD-1"
        assert result.status == "created"
        assert result.total == 1500.0

    def test_create_empty_result(self) -> None:
        """Empty subclass creates without error."""
        result = EmptyResult()
        assert result.keys() == []

    def test_pydantic_validation(self) -> None:
        """Pydantic validates types and constraints on creation."""
        with pytest.raises(ValidationError):
            OrderResult(order_id="ORD-1", status="created", total=-1.0)

    def test_getitem_access(self) -> None:
        """Dict-like access via brackets (BaseSchema)."""
        result = OrderResult(order_id="ORD-1", status="created", total=100.0)
        assert result["order_id"] == "ORD-1"
        assert result["status"] == "created"

    def test_getitem_missing_raises(self) -> None:
        """Missing key raises KeyError."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises(KeyError):
            _ = result["nonexistent"]

    def test_get_with_default(self) -> None:
        """get() returns default for missing key."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert result.get("order_id") == "ORD-1"
        assert result.get("missing") is None
        assert result.get("missing", "fallback") == "fallback"

    def test_contains(self) -> None:
        """``in`` checks key presence."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert "order_id" in result
        assert "missing" not in result

    def test_keys_values_items(self) -> None:
        """keys, values, items return correct data."""
        result = OrderResult(order_id="ORD-1", status="ok", total=50.0)
        assert set(result.keys()) == {"order_id", "status", "total"}
        assert "ORD-1" in result.values()
        assert ("status", "ok") in result.items()

    def test_resolve(self) -> None:
        """resolve() works for flat keys."""
        result = OrderResult(order_id="ORD-1", status="ok", total=99.9)
        assert result.resolve("total") == 99.9
        assert result.resolve("missing") is None

    def test_model_dump(self) -> None:
        """model_dump() serializes all declared fields."""
        result = OrderResult(order_id="ORD-1", status="ok", total=100.0)
        assert result.model_dump() == {"order_id": "ORD-1", "status": "ok", "total": 100.0}

    def test_model_json_schema(self) -> None:
        """model_json_schema() builds JSON Schema with descriptions."""
        schema = OrderResult.model_json_schema()
        props = schema.get("properties", {})
        assert "order_id" in props
        assert props["order_id"].get("description") == "Order ID"


# ═════════════════════════════════════════════════════════════════════════════
# Frozen semantics: writes forbidden
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultFrozen:
    """Immutability of BaseResult after creation."""

    def test_setattr_existing_raises(self) -> None:
        """Changing an existing field raises ValidationError."""
        result = OrderResult(order_id="ORD-1", status="created", total=100.0)
        with pytest.raises(ValidationError):
            result.status = "paid"

    def test_setattr_new_field_raises(self) -> None:
        """New attribute forbidden — ValidationError (extra="forbid")."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((ValidationError, TypeError, AttributeError)):
            result.debug_info = "test"

    def test_extra_fields_forbidden_at_creation(self) -> None:
        """Arbitrary fields at construction forbidden (extra="forbid")."""
        with pytest.raises(ValidationError):
            OrderResult(
                order_id="ORD-1",
                status="ok",
                total=0.0,
                unexpected_field="surprise",
            )

    def test_setitem_raises(self) -> None:
        """Dict-like write via [] not supported (frozen BaseResult, no __setitem__)."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((TypeError, AttributeError)):
            result["status"] = "new"

    def test_delitem_raises(self) -> None:
        """Dict-like del via [] not supported."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((TypeError, AttributeError)):
            del result["status"]

    def test_write_method_missing(self) -> None:
        """write() does not exist."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert not hasattr(result, "write")

    def test_update_method_missing(self) -> None:
        """update() does not exist."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert not hasattr(result, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Update pattern — model_copy
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultImmutableUpdate:
    """Updates via model_copy (pydantic)."""

    def test_model_copy_creates_new_instance(self) -> None:
        """model_copy(update=...) creates a new frozen instance."""
        original = OrderResult(order_id="ORD-1", status="created", total=100.0)
        updated = original.model_copy(update={"status": "paid"})
        assert updated.status == "paid"
        assert updated.order_id == "ORD-1"
        assert updated.total == 100.0
        assert original.status == "created"

    def test_model_copy_is_different_object(self) -> None:
        """model_copy returns a new object, not the same reference."""
        original = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        copy = original.model_copy()
        assert copy is not original
        assert copy.model_dump() == original.model_dump()

    def test_model_copy_result_is_also_frozen(self) -> None:
        """model_copy result is still frozen — writes raise."""
        original = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        copy = original.model_copy(update={"status": "paid"})
        with pytest.raises(ValidationError):
            copy.status = "refunded"
