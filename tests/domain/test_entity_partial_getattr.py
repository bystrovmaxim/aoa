# tests/domain/test_entity_partial_getattr.py
"""BaseEntity.partial() and __getattr__ for unloaded vs unknown attributes."""

from __future__ import annotations

import pytest

from action_machine.domain.exceptions import FieldNotLoadedError
from tests.scenarios.domain_model.entities import SampleEntity


def test_partial_access_to_unloaded_model_field_raises_field_not_loaded() -> None:
    entity = SampleEntity.partial(id="only-id")
    with pytest.raises(FieldNotLoadedError, match="name"):
        _ = entity.name


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
