# tests/domain/test_hydration.py
"""
Tests for entity **hydration** — building instances from plain data.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers:
- `build()` construction path
- `EntityProxy` placeholder access during hydration
- Nested / partial payloads where applicable
- Validation errors from Pydantic

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValidationError** — payload does not match the entity model.

`build()` behavior for nested and partial graphs is covered only as far as
this file asserts; edge cases may live in integration tests.
"""

import pytest
from pydantic import ValidationError

from action_machine.domain import build
from tests.domain_model.entities import RelatedEntity, SampleEntity


class TestBuildFunction:
    """Tests for `build()`."""

    def test_build_simple_entity(self):
        """Construct a simple entity from a dict."""
        data = {
            "id": "123",
            "name": "Test Entity",
            "value": 42,
        }

        entity = build(data, SampleEntity)

        assert isinstance(entity, SampleEntity)
        assert entity.id == "123"
        assert entity.name == "Test Entity"
        assert entity.value == 42

    def test_build_with_validation(self):
        """Invalid field values raise `ValidationError`."""
        # Valid payload
        data = {"id": "123", "name": "Test", "value": 10}
        entity = build(data, SampleEntity)
        assert entity.value == 10

        # Invalid payload
        data_invalid = {"id": "123", "name": "Test", "value": -1}
        with pytest.raises(ValidationError):
            build(data_invalid, SampleEntity)

    def test_build_with_relations(self):
        """Explicit ``None`` for optional relation fields."""
        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
            "children": None,
        }

        entity = build(data, RelatedEntity)

        assert isinstance(entity, RelatedEntity)
        assert entity.id == "parent-123"
        assert entity.title == "Parent Entity"
        assert entity.parent is None
        assert entity.children is None

    def test_build_without_optional_relations(self):
        """Omitted optional relation key keeps class-level `Rel` default."""
        from action_machine.domain.relation_markers import Rel

        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
        }

        entity = build(data, RelatedEntity)

        assert entity.id == "parent-123"
        # `children` not in input → pydantic uses field default (`Rel(...)`)
        assert isinstance(entity.children, Rel)

    def test_build_partial_data(self):
        """Missing required scalar fields → `ValidationError`."""
        data = {"id": "123", "name": "Test"}
        with pytest.raises(ValidationError):
            build(data, SampleEntity)

    def test_build_extra_fields(self):
        """Undeclared keys are rejected (`extra='forbid'`)."""
        data = {
            "id": "123",
            "name": "Test",
            "value": 42,
            "extra_field": "not allowed",
        }

        with pytest.raises(ValidationError):
            build(data, SampleEntity)


class TestEntityProxy:
    """Tests for `EntityProxy` (internal helper used by `build`)."""

    def test_proxy_creation(self):
        """Placeholder attribute names match model field names."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            field1: str
            field2: int

        proxy = EntityProxy(DummyEntity)

        assert proxy.field1 == "field1"
        assert proxy.field2 == "field2"

    def test_proxy_missing_field(self):
        """Unknown attribute name → `AttributeError`."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            existing: str

        proxy = EntityProxy(DummyEntity)

        with pytest.raises(AttributeError):
            _ = proxy.missing_field

    def test_proxy_getattr(self):
        """`__getattr__` resolves declared field placeholders."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            test: str

        proxy = EntityProxy(DummyEntity)

        assert proxy.test == "test"
        assert proxy.__getattr__("test") == "test"
        with pytest.raises(AttributeError):
            proxy.__getattr__("missing")
