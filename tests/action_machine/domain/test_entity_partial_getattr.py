# tests/domain/test_entity_partial_getattr.py
"""BaseEntity.partial() and __getattr__ for unloaded vs unknown attributes."""

from __future__ import annotations

import pytest

from aoa.action_machine.domain.exceptions import FieldNotLoadedError
from tests.action_machine.scenarios.domain_model.entities import LifecycleEntity, SampleEntity


def test_partial_access_to_unloaded_model_field_raises_field_not_loaded() -> None:
    entity = SampleEntity.partial(id="only-id")
    with pytest.raises(FieldNotLoadedError, match="name"):
        _ = entity.name


def test_field_not_loaded_error_exposes_contract_attributes() -> None:
    """Regression: exception carries field_name, class name, and loaded subset."""
    entity = SampleEntity.partial(id="only-id")
    with pytest.raises(FieldNotLoadedError) as exc_info:
        _ = entity.value

    err = exc_info.value
    assert err.field_name == "value"
    assert err.entity_class_name == "SampleEntity"
    assert err.loaded_fields == frozenset({"id"})


def test_lifecycle_entity_partial_missing_field_raises_field_not_loaded() -> None:
    """Regression: union-typed model field uses the same partial access path."""
    entity = LifecycleEntity.partial(id="e1")
    with pytest.raises(FieldNotLoadedError, match="lifecycle") as exc_info:
        _ = entity.lifecycle

    assert exc_info.value.field_name == "lifecycle"
    assert exc_info.value.entity_class_name == "LifecycleEntity"
    assert exc_info.value.loaded_fields == frozenset({"id"})


def test_partial_access_to_unknown_attribute_raises_attribute_error() -> None:
    entity = SampleEntity.partial(id="only-id")
    with pytest.raises(AttributeError, match="no attribute 'not_a_field'"):
        _ = entity.not_a_field


def test_partial_model_field_marked_loaded_is_readable() -> None:
    entity = SampleEntity.partial(id="x", name="y")
    assert entity.id == "x"
    assert entity.name == "y"


def test_full_entity_getattr_unknown_still_attribute_error() -> None:
    entity = SampleEntity(id="1", name="n", value=0)
    with pytest.raises(AttributeError):
        _ = entity.unknown_attr  # type: ignore[attr-defined]


def test_construct_without_partial_flag_missing_model_field_attribute_error() -> None:
    """Declared field missing and no ``_partial_instance`` → generic ``AttributeError``."""
    entity = SampleEntity.model_construct(id="only-id")
    with pytest.raises(AttributeError, match="name"):
        _ = entity.name
