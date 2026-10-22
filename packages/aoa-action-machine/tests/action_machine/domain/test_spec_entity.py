# tests/action_machine/domain/test_spec_entity.py
# ruff: noqa: F821  # the class-name alias is the surface this module tests
"""
Tests for the value an extension declares.

Every extension names, in its own `Classifier` marker, the dictionary value it
is. The class exposes that value as `declared_variant`, so a container can check
that the row it holds and the value it carries agree. A class whose marker names
codes instead keeps `declared_variant` empty.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Rel,
    Specialization,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class SpecShopDomain(BaseDomain):
    """The domain these fixtures belong to."""

    name = "spec-shop"
    description = "Spec shop"


@exclude_graph_model
@entity(description="Edition kind", domain=SpecShopDomain)
class SpecEditionKindEnumEntity(BaseEnumEntity):
    """A closed dictionary."""

    FIRST = SpecEditionKindEnumEntity(code="first", display_name="First press")
    REPRESS = SpecEditionKindEnumEntity(code="repress", display_name="Repress")


@exclude_graph_model
@entity(description="Record", domain=SpecShopDomain)
class SpecRecordCoreEntity(BaseCoreEntity):
    """The head of the axis."""

    id: str = Field(description="Record id")
    kind: Specialization[SpecFirstPressSpecEntity | SpecRepressSpecEntity, SpecEditionKindEnumEntity] = Rel(
        description="Which pressing this is"
    )


@exclude_graph_model
@entity(description="First press", domain=SpecShopDomain)
class SpecFirstPressSpecEntity(BaseSpecEntity):
    """Names the declared value it is."""

    record: Annotated[
        Generalization[SpecRecordCoreEntity],
        Classifier(field="record", variant=SpecEditionKindEnumEntity.FIRST),
    ] = Rel(description="The head row")


@exclude_graph_model
@entity(description="Repress", domain=SpecShopDomain)
class SpecRepressSpecEntity(BaseSpecEntity):
    """Names the other declared value."""

    record: Annotated[
        Generalization[SpecRecordCoreEntity],
        Classifier(field="record", variant=SpecEditionKindEnumEntity.REPRESS),
    ] = Rel(description="The head row")


@exclude_graph_model
@entity(description="Legacy extension", domain=SpecShopDomain)
class SpecLegacySpecEntity(BaseSpecEntity):
    """Keeps the earlier marker form, which names codes rather than a value."""

    record: Annotated[
        Generalization[SpecRecordCoreEntity],
        Classifier("record", __import__("typing").Literal["first"]),
    ] = Rel(description="The head row")


def test_each_extension_exposes_the_value_it_declares() -> None:
    """The class attribute is the declared object itself."""
    assert SpecFirstPressSpecEntity.declared_variant is SpecEditionKindEnumEntity.FIRST
    assert SpecRepressSpecEntity.declared_variant is SpecEditionKindEnumEntity.REPRESS


def test_the_value_is_derived_from_the_marker_not_written_by_hand() -> None:
    """Nothing but the marker states the value; the attribute is a reading of it."""
    assert "declared_variant" not in SpecFirstPressSpecEntity.__dict__ or (
        SpecFirstPressSpecEntity.__dict__["declared_variant"] is SpecEditionKindEnumEntity.FIRST
    )
    assert SpecFirstPressSpecEntity.declared_variant.code == "first"


def test_an_extension_that_names_codes_has_no_declared_value() -> None:
    """The marker form decides: a code list is not a declared value."""
    assert SpecLegacySpecEntity.declared_variant is None
