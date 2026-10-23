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

from aoa.action_machine.domain import BaseCoreEntity, build
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity

from ...support.domain_model.entities import RelatedCoreEntity, SampleCoreEntity


class _HydrationTestDomain(BaseDomain):
    name = "hydration_test"
    description = "Domain for hydration tests."


class TestBuildFunction:
    """Tests for `build()`."""

    def test_build_simple_entity(self):
        """Construct a simple entity from a dict."""
        data = {
            "id": "123",
            "name": "Test Entity",
            "value": 42,
        }

        entity = build(data, SampleCoreEntity)

        assert isinstance(entity, SampleCoreEntity)
        assert entity.id == "123"
        assert entity.name == "Test Entity"
        assert entity.value == 42

    def test_build_with_validation(self):
        """Invalid field values raise `ValidationError`."""
        # Valid payload
        data = {"id": "123", "name": "Test", "value": 10}
        entity = build(data, SampleCoreEntity)
        assert entity.value == 10

        # Invalid payload
        data_invalid = {"id": "123", "name": "Test", "value": -1}
        with pytest.raises(ValidationError):
            build(data_invalid, SampleCoreEntity)

    def test_build_with_relations(self):
        """Explicit ``None`` for optional relation fields."""
        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
            "children": None,
        }

        entity = build(data, RelatedCoreEntity)

        assert isinstance(entity, RelatedCoreEntity)
        assert entity.id == "parent-123"
        assert entity.title == "Parent Entity"
        assert entity.parent is None
        assert entity.children is None

    def test_build_without_optional_relations(self):
        """An omittable relation yields ``None``: its default is the absence, not a marker."""
        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
        }

        entity = build(data, RelatedCoreEntity)

        assert entity.id == "parent-123"
        assert entity.children is None

    def test_build_partial_data(self):
        """Missing required scalar fields → `ValidationError`."""
        data = {"id": "123", "name": "Test"}
        with pytest.raises(ValidationError):
            build(data, SampleCoreEntity)

    def test_build_extra_fields(self):
        """Undeclared keys are rejected (`extra='forbid'`)."""
        data = {
            "id": "123",
            "name": "Test",
            "value": 42,
            "extra_field": "not allowed",
        }

        with pytest.raises(ValidationError):
            build(data, SampleCoreEntity)


class TestEntityProxy:
    """Tests for `EntityProxy` (internal helper used by `build`)."""

    def test_proxy_creation(self):
        """Placeholder attribute names match model field names."""
        from aoa.action_machine.domain.hydration import EntityProxy

        @entity(description="Proxy creation dummy", domain=_HydrationTestDomain)
        class DummyCoreEntity(BaseCoreEntity):
            field1: str
            field2: int

        proxy = EntityProxy(DummyCoreEntity)

        assert proxy.field1 == "field1"
        assert proxy.field2 == "field2"

    def test_proxy_missing_field(self):
        """Unknown attribute name → `AttributeError`."""
        from aoa.action_machine.domain.hydration import EntityProxy

        @entity(description="Proxy missing field dummy", domain=_HydrationTestDomain)
        class DummyCoreEntity(BaseCoreEntity):
            existing: str

        proxy = EntityProxy(DummyCoreEntity)

        with pytest.raises(AttributeError):
            _ = proxy.missing_field

    def test_proxy_getattr(self):
        """`__getattr__` resolves declared field placeholders."""
        from aoa.action_machine.domain.hydration import EntityProxy

        @entity(description="Proxy getattr dummy", domain=_HydrationTestDomain)
        class DummyCoreEntity(BaseCoreEntity):
            test: str

        proxy = EntityProxy(DummyCoreEntity)

        assert proxy.test == "test"
        assert proxy.__getattr__("test") == "test"
        with pytest.raises(AttributeError):
            proxy.__getattr__("missing")
