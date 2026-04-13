# tests/domain/test_entity.py
"""
Tests for `BaseEntity` and the `@entity` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers decorator validation, inheritance, frozen semantics, dict-like access,
dot-path helpers (via `BaseSchema`), and serialization checks.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY
═══════════════════════════════════════════════════════════════════════════════

**Entity** — Pydantic `BaseEntity` subclass with `@entity(...)`. **Decorator**
attaches `_entity_info` at class creation time.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **EntityDecoratorError** — invalid `@entity` usage (description, domain type,
  missing `BaseEntity` inheritance).
- **NamingSuffixError** — class name must end with `Entity`.
- **ValidationError** — Pydantic validation on construct / dump where tested.

Coordinator graph/metadata assembly is covered in metadata tests.
"""

import pytest
from pydantic import ValidationError

from action_machine.domain import BaseEntity, entity
from action_machine.domain.entity_decorator import EntityDecoratorError
from action_machine.model.exceptions import NamingSuffixError
from tests.scenarios.domain_model.entities import SampleEntity, TestDomain


class TestEntityDecorator:
    """Tests for the `@entity` decorator."""

    def test_valid_entity_creation(self):
        """Happy path: decorated entity gets `_entity_info`."""
        @entity(description="Test entity fixture", domain=TestDomain)
        class ValidEntity(BaseEntity):
            id: str
            name: str

        assert hasattr(ValidEntity, "_entity_info")
        assert ValidEntity._entity_info["description"] == "Test entity fixture"
        assert ValidEntity._entity_info["domain"] == TestDomain

    def test_missing_description(self):
        """Empty description is rejected."""
        with pytest.raises(EntityDecoratorError, match="description cannot be empty"):
            @entity(description="", domain=TestDomain)
            class InvalidEntity(BaseEntity):
                id: str

    def test_invalid_domain(self):
        """Non-domain `domain` argument is rejected."""
        with pytest.raises(EntityDecoratorError):
            @entity(description="Test", domain="not_a_domain")
            class InvalidEntity(BaseEntity):
                id: str

    def test_no_inheritance_from_base_entity(self):
        """Decorator requires a `BaseEntity` subclass."""
        with pytest.raises(EntityDecoratorError):
            @entity(description="Test")
            class InvalidEntity:
                id: str


class TestBaseEntity:
    """Tests for `BaseEntity`."""

    def test_class_name_must_end_with_entity_suffix(self) -> None:
        """Subclass name must end with ``Entity`` (`NamingSuffixError`)."""
        with pytest.raises(NamingSuffixError, match="inherits from BaseEntity"):
            class Order(BaseEntity):
                pass

    def test_entity_creation(self):
        """Construct a fully validated entity instance."""
        entity = SampleEntity(id="123", name="Test", value=42)
        assert entity.id == "123"
        assert entity.name == "Test"
        assert entity.value == 42

    def test_frozen_semantics(self):
        """Mutation of fields is forbidden (`frozen=True`)."""
        entity = SampleEntity(id="123", name="Test", value=42)

        with pytest.raises(ValidationError):
            entity.value = 100

    def test_dict_access(self):
        """Bracket and membership access work like a mapping."""
        entity = SampleEntity(id="123", name="Test", value=42)

        assert entity["id"] == "123"
        assert "name" in entity
        assert entity["value"] == 42

    def test_model_dump(self):
        """`model_dump` returns a plain dict of field values."""
        entity = SampleEntity(id="123", name="Test", value=42)
        data = entity.model_dump()

        assert data == {"id": "123", "name": "Test", "value": 42}

    def test_validation(self):
        """Pydantic validates field constraints."""
        # Valid payload
        entity = SampleEntity(id="123", name="Test", value=42)
        assert entity.value == 42

        # Invalid payload
        with pytest.raises(ValidationError):
            SampleEntity(id="123", name="Test", value=-1)  # value >= 0

    def test_extra_fields_forbid(self):
        """Undeclared keys are rejected (`extra='forbid'`)."""
        with pytest.raises(ValidationError):
            SampleEntity(id="123", name="Test", value=42, extra_field="not_allowed")
