# tests/action_machine/domain/test_declared_values.py
# ruff: noqa: F821  # the class-name alias is the surface these tests exercise
"""
Tests for the declaration machinery shared by the kinds that declare values.

Covers the mixin staying out of the kind hierarchy, the placeholder never
becoming a model field, the class-name alias raising for unknown names, and the
two per-kind switches: own-class catalogue and the duplicate refusal's wording.

The fixture derives from the state kind rather than declaring a new kind base, so
the "exactly six kind bases" rule stays untouched and the graph walk skips these
classes through the state kind's own exclusion.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.domain import BaseStateEntity
from aoa.action_machine.domain.declared_values import (
    ValueSpec,
    _DeclaredValues,
    value,
)
from aoa.action_machine.domain.entity import BaseEntity, _is_kind_base


class OwnCatalogueStateEntity(BaseStateEntity):
    """A state-kind fixture that keeps its own values and inherits none."""

    __declared_values_inherit__ = False
    __declared_values_noun__ = "value"


class ParentFixtureStateEntity(OwnCatalogueStateEntity):
    """A fixture class that declares two values."""

    ALPHA = ParentFixtureStateEntity(code="alpha", display_name="Alpha")
    BETA = ParentFixtureStateEntity(code="beta", display_name="Beta")


class ChildFixtureStateEntity(ParentFixtureStateEntity):
    """A fixture subclass that declares nothing of its own."""


def test_the_mixin_is_not_a_kind_base() -> None:
    """The mixin inherits nothing, so the hierarchy never counts it as a kind."""
    assert BaseEntity not in _DeclaredValues.__bases__
    assert _is_kind_base(_DeclaredValues) is False
    assert _is_kind_base(BaseStateEntity) is True


def test_the_placeholder_becomes_an_instance_and_never_a_field() -> None:
    """Every declared name is a real instance of the declaring type, not a model field."""
    assert isinstance(ParentFixtureStateEntity.ALPHA, ParentFixtureStateEntity)
    assert ParentFixtureStateEntity.ALPHA.code == "alpha"
    assert isinstance(ParentFixtureStateEntity.BETA, ValueSpec) is False
    assert "ALPHA" not in ParentFixtureStateEntity.model_fields
    assert "BETA" not in ParentFixtureStateEntity.model_fields


def test_the_catalogue_keeps_declaration_order() -> None:
    """The catalogue is the declared values in the order they were written."""
    assert ParentFixtureStateEntity.codes() == ["alpha", "beta"]
    assert ParentFixtureStateEntity.by_code("beta") is ParentFixtureStateEntity.BETA
    assert ParentFixtureStateEntity.members == (
        ParentFixtureStateEntity.ALPHA,
        ParentFixtureStateEntity.BETA,
    )
    assert ParentFixtureStateEntity.entity_type is ParentFixtureStateEntity


def test_a_non_inheriting_kind_starts_a_subclass_with_no_values() -> None:
    """A class of a non-inheriting kind does not take its parent's catalogue."""
    assert ChildFixtureStateEntity.members == ()
    assert ChildFixtureStateEntity.codes() == []
    with pytest.raises(KeyError):
        ChildFixtureStateEntity.by_code("alpha")


def test_an_unknown_name_in_the_class_body_still_raises() -> None:
    """Only the declaring type's own name resolves to the factory; anything else is a NameError."""
    with pytest.raises(NameError):

        class BrokenFixtureStateEntity(ParentFixtureStateEntity):
            """Reference an undefined name, as any class body would."""

            GAMMA = MISSING_FACTORY(code="gamma", display_name="Gamma")


def test_the_duplicate_refusal_uses_the_kind_wording() -> None:
    """A kind names what its values are called, so the duplicate message reads naturally."""
    with pytest.raises(ValueError, match="duplicate value code"):

        class DuplicateFixtureStateEntity(OwnCatalogueStateEntity):
            """Declare the same code twice."""

            ONE = DuplicateFixtureStateEntity(code="same", display_name="One")
            TWO = DuplicateFixtureStateEntity(code="same", display_name="Two")


def test_the_declaration_factory_is_plain() -> None:
    """The factory is a plain function returning a placeholder, usable outside a class body."""
    spec = value(code="x", display_name="X")
    assert isinstance(spec, ValueSpec)
    assert spec.kwargs == {"code": "x", "display_name": "X"}
