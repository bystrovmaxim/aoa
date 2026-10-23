# tests/action_machine/domain/test_declared_values.py
"""
Tests for the declaration machinery shared by the kinds that declare values.

Covers the mixin staying out of the kind hierarchy, the placeholder never
becoming a model field, the explicit ``value(...)`` factory, and the two
per-kind switches: own-class catalogue and the duplicate refusal's wording.

The fixture derives from the state kind rather than declaring a new kind base, so
the "exactly six kind bases" rule stays untouched and the graph walk skips these
classes through the state kind's own exclusion.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseStateEntity, value
from aoa.action_machine.domain.declared_values import (
    ValueSpec,
    _DeclaredValues,
)
from aoa.action_machine.domain.entity import BaseEntity, _is_kind_base


class OwnCatalogueStateEntity(BaseStateEntity):
    """A state-kind fixture that keeps its own values and inherits none."""

    __declared_values_inherit__ = False
    __declared_values_noun__ = "value"


class ParentFixtureStateEntity(OwnCatalogueStateEntity):
    """A fixture class that declares two values."""

    ALPHA = value(code="alpha", display_name="Alpha")
    BETA = value(code="beta", display_name="Beta")


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


def test_a_class_body_naming_its_own_class_fails() -> None:
    """The removed form cannot work: the class name does not exist while its body runs."""
    source = (
        "class RemovedFormStateEntity(ParentFixtureStateEntity):\n"
        '    """Declare a value with the class name, as the removed alias allowed."""\n'
        "\n"
        '    GAMMA = RemovedFormStateEntity(code="gamma", display_name="Gamma")\n'
    )
    with pytest.raises(NameError):
        exec(source, {"ParentFixtureStateEntity": ParentFixtureStateEntity})


def test_the_duplicate_refusal_uses_the_kind_wording() -> None:
    """A kind names what its values are called, so the duplicate message reads naturally."""
    with pytest.raises(ValueError, match="duplicate value code"):

        class DuplicateFixtureStateEntity(OwnCatalogueStateEntity):
            """Declare the same code twice."""

            ONE = value(code="same", display_name="One")
            TWO = value(code="same", display_name="Two")


def test_the_declaration_factory_is_plain() -> None:
    """The factory is a plain function returning a placeholder, usable outside a class body."""
    spec = value(code="x", display_name="X")
    assert isinstance(spec, ValueSpec)
    assert spec.kwargs == {"code": "x", "display_name": "X"}


def test_a_field_named_value_needs_the_factory_under_another_name() -> None:
    """A class body that binds ``value`` shadows the factory; an alias declares it, and it works."""
    from aoa.action_machine.domain import value as declared

    class FieldNamedValueStateEntity(BaseStateEntity):
        """Carry a field called like the factory, and declare a status anyway."""

        value: int = Field(default=1, description="A field named like the factory")
        A = declared(code="a", display_name="A")

    assert FieldNamedValueStateEntity.codes() == ["a"]
    assert FieldNamedValueStateEntity.A.value == 1
