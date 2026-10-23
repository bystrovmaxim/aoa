# tests/action_machine/domain/test_spec_entity.py
# the class-name alias is the surface this module tests
"""
Tests for the value an extension declares.

Every extension names, in its own `Classifier` marker, the dictionary value it
is. The class exposes that value as `declared_variant`, so a container can check
that the row it holds and the value it carries agree. A class without a marker exposes no declared variant.
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
    value,
)
from aoa.action_machine.domain.spec_entity import declared_value
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

    FIRST = value(code="first", display_name="First press")
    REPRESS = value(code="repress", display_name="Repress")


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
@entity(description="Unmarked extension", domain=SpecShopDomain)
class SpecUnmarkedSpecEntity(BaseSpecEntity):
    """Points back at its head without naming a value."""

    record: Generalization[SpecRecordCoreEntity] = Rel(description="The head row")


def test_each_extension_exposes_the_value_it_declares() -> None:
    """The class attribute is the declared object itself."""
    assert declared_value(SpecFirstPressSpecEntity) is SpecEditionKindEnumEntity.FIRST
    assert declared_value(SpecRepressSpecEntity) is SpecEditionKindEnumEntity.REPRESS


def test_the_value_is_derived_from_the_marker_not_written_by_hand() -> None:
    """Nothing but the marker states the value; the attribute is a reading of it."""
    assert declared_value(SpecFirstPressSpecEntity) is SpecEditionKindEnumEntity.FIRST
    assert declared_value(SpecFirstPressSpecEntity).code == "first"


def test_an_extension_that_names_no_value_has_none() -> None:
    """The marker decides; without one, the class declares nothing."""
    assert declared_value(SpecUnmarkedSpecEntity) is None


def test_declared_variant_is_available_after_resolving_a_forward_head() -> None:
    """Declaration order must not leave the public variant attribute empty."""
    @exclude_graph_model
    class EarlierSpecEntity(BaseSpecEntity):
        """Describe a head declared later in the module."""
        record: Annotated[
            Generalization[LaterCoreEntity],
            Classifier(field="record", variant=SpecEditionKindEnumEntity.FIRST),
        ]

    @exclude_graph_model
    class LaterCoreEntity(BaseCoreEntity):
        """Provide the forward target."""
        id: str

    EarlierSpecEntity.model_rebuild(_types_namespace={"LaterCoreEntity": LaterCoreEntity})
    assert EarlierSpecEntity.declared_variant is SpecEditionKindEnumEntity.FIRST
