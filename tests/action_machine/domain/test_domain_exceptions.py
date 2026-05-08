# tests/domain/test_domain_exceptions.py
"""Constructors and messages for domain-layer exceptions."""

from __future__ import annotations

import pytest

from aoa.action_machine.domain.exceptions import (
    FieldNotLoadedError,
    LifecycleValidationError,
    RelationNotLoadedError,
)


def test_field_not_loaded_error_with_loaded_fields() -> None:
    err = FieldNotLoadedError(
        field_name="status",
        entity_class_name="OrderEntity",
        loaded_fields=frozenset({"id", "name"}),
    )
    assert err.field_name == "status"
    assert "status" in str(err)
    assert "id, name" in str(err) or "name, id" in str(err)


def test_field_not_loaded_error_empty_loaded_fields_uses_none_label() -> None:
    err = FieldNotLoadedError(
        field_name="x",
        entity_class_name="E",
        loaded_fields=frozenset(),
    )
    assert "(none)" in str(err)


def test_relation_not_loaded_error_message() -> None:
    err = RelationNotLoadedError("AssociationOne", "name", 42)
    assert err.container_class_name == "AssociationOne"
    assert "42" in str(err)
    assert "name" in str(err)


def test_lifecycle_validation_error_message() -> None:
    err = LifecycleValidationError("Order", "status_lc", "no final state")
    assert err.entity_name == "Order"
    assert err.field_name == "status_lc"
    assert err.details == "no final state"
    assert "status_lc" in str(err)
    assert "no final state" in str(err)


def test_entity_decorator_error_is_type_error() -> None:
    from aoa.action_machine.domain.exceptions import EntityDecoratorError

    assert issubclass(EntityDecoratorError, TypeError)
    with pytest.raises(EntityDecoratorError):
        raise EntityDecoratorError()
