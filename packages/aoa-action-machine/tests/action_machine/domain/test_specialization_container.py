# tests/action_machine/domain/test_specialization_container.py
"""
Tests for the specialization container when its second type argument is a dictionary.

The container holds a declared value; a bare code, an unknown code and a value
that disagrees with the hydrated row are refused; the value serializes as its
reference object. The retired one-argument form is refused.
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import Field, ValidationError

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
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class ContainerShopDomain(BaseDomain):
    """The domain these fixtures belong to."""

    name = "container-shop"
    description = "Container shop"


@exclude_graph_model
@entity(description="Edition kind", domain=ContainerShopDomain)
class ContainerEditionKindEnumEntity(BaseEnumEntity):
    """A closed dictionary the axis is classified by."""

    note: str = Field(default="", description="Free note")

    FIRST = value(code="first", display_name="First press")
    REPRESS = value(code="repress", display_name="Repress")


@exclude_graph_model
@entity(description="Record", domain=ContainerShopDomain)
class ContainerRecordCoreEntity(BaseCoreEntity):
    """The head whose field is the container."""

    id: str = Field(description="Record id")
    kind: Specialization[ContainerFirstPressSpecEntity | ContainerRepressSpecEntity, ContainerEditionKindEnumEntity] = Rel(
        description="Which pressing this is"
    )


@exclude_graph_model
@entity(description="First press", domain=ContainerShopDomain)
class ContainerFirstPressSpecEntity(BaseSpecEntity):
    """The first-press extension."""

    record: Annotated[
        Generalization[ContainerRecordCoreEntity],
        Classifier(variant=ContainerEditionKindEnumEntity.FIRST),
    ] = Rel(description="The head row")


@exclude_graph_model
@entity(description="Repress", domain=ContainerShopDomain)
class ContainerRepressSpecEntity(BaseSpecEntity):
    """The repress extension."""

    record: Annotated[
        Generalization[ContainerRecordCoreEntity],
        Classifier(variant=ContainerEditionKindEnumEntity.REPRESS),
    ] = Rel(description="The head row")


ContainerVariant = Specialization[
    ContainerFirstPressSpecEntity | ContainerRepressSpecEntity,
    ContainerEditionKindEnumEntity,
]


def test_the_container_holds_the_declared_value() -> None:
    """A declared value enters as itself."""
    container = ContainerVariant(id="p1", variant=ContainerEditionKindEnumEntity.FIRST)

    assert container.variant is ContainerEditionKindEnumEntity.FIRST
    assert container.variant.code == "first"


def test_the_container_serializes_the_reference_object() -> None:
    """The wire form is the value's reference form, not its code alone."""
    container = ContainerVariant(id="p1", variant=ContainerEditionKindEnumEntity.REPRESS)

    dumped: dict[str, Any] = container.model_dump()
    assert dumped["variant"] == {"code": "repress", "display_name": "Repress", "properties": {"note": ""}}


def test_a_bare_code_is_refused_by_a_dictionary_typed_container() -> None:
    """The resource resolves the stored code before the model sees it."""
    with pytest.raises(ValidationError, match="bare code is not accepted"):
        ContainerVariant(id="p1", variant="first")


def test_an_undeclared_code_is_refused() -> None:
    """A reference object is resolved by its code, and the set is closed."""
    with pytest.raises(ValidationError, match="is not a declared value"):
        ContainerVariant(id="p1", variant={"code": "bootleg"})


def test_a_copy_of_a_declared_value_is_refused() -> None:
    """A copy is not a declared value."""
    copy = ContainerEditionKindEnumEntity(code="first", display_name="First press", note="mine")

    with pytest.raises(ValidationError, match="a copy of a declared value is not a value"):
        ContainerVariant(id="p1", variant=copy)


def test_the_container_refuses_a_value_that_disagrees_with_the_row() -> None:
    """The value and the hydrated class must state the same variant."""
    with pytest.raises(ValidationError, match="does not match ContainerRepressSpecEntity"):
        ContainerVariant(
            id="p1",
            variant=ContainerEditionKindEnumEntity.FIRST,
            entity=ContainerRepressSpecEntity.partial(record=None),
        )


def test_the_container_accepts_a_matching_pair() -> None:
    """A value that agrees with the hydrated class passes."""
    container = ContainerVariant(
        id="p1",
        variant=ContainerEditionKindEnumEntity.FIRST,
        entity=ContainerFirstPressSpecEntity.partial(record=None),
    )

    assert container.variant is ContainerEditionKindEnumEntity.FIRST
    assert isinstance(container.entity, ContainerFirstPressSpecEntity)


def test_an_absent_row_keeps_the_value_known() -> None:
    """The variant may be known while the extension row was not loaded."""
    container = ContainerVariant(id="p1", variant=ContainerEditionKindEnumEntity.FIRST, entity=None)

    assert container.entity is None
    assert container.variant.code == "first"


def test_a_container_must_name_its_dictionary() -> None:
    """The one-argument form is gone: a container without a dictionary is a TypeError."""
    with pytest.raises(TypeError, match="Too few arguments"):
        Specialization[ContainerFirstPressSpecEntity | ContainerRepressSpecEntity]


def test_matching_codes_from_different_dictionaries_do_not_make_a_matching_pair() -> None:
    """A loaded class must declare the exact selected value."""
    @exclude_graph_model
    class OtherEditionEnumEntity(BaseEnumEntity):
        """Reuse a code in an independent dictionary."""
        FIRST = value(code="first", display_name="Another first")

    with pytest.raises(ValidationError, match="does not match"):
        Specialization[ContainerFirstPressSpecEntity, OtherEditionEnumEntity](
            id="p1", variant=OtherEditionEnumEntity.FIRST,
            entity=ContainerFirstPressSpecEntity.partial(record=None),
        )
