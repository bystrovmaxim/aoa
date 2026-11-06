"""Specialization cannot form a cycle.
Run: .venv/bin/python examples/step_24_relations/37_error_cycle.py


Make two classes specialize one another.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Specialization,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class MusicDomain(BaseDomain):
    """Group the cycle experiment."""

    name = "music"
    description = "Cycle experiment"


@meta(description="Where MusicStorage keeps its rows")
class MusicDataSource(InMemoryDataSource):
    """The store MusicStorage works with."""


@meta(description="Stores the music entities", domain=MusicDomain)
class MusicStorage(BaseStorage[MusicDataSource]):
    """Hold the music entities."""


@entity(description="Kind of ASpecEntity", resource=MusicStorage)
class ASpecEntityKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    B = value(code="b", display_name="B")


@entity(description="First level", resource=MusicStorage)
class ASpecEntity(BaseSpecEntity):
    """Declare the first level of detail."""

    id: str = Field(description="Identifier")
    detail: Annotated[Specialization[BSpecEntity, ASpecEntityKindEnumEntity], Inverse(field_name="back")] = Field(
        description="Next level"
    )
    back: Annotated[
        Generalization[BSpecEntity],
        Classifier(variant=BSpecEntityKindEnumEntity.A),
        Inverse(field_name="detail"),
    ] = Field(description="Return to B")


@entity(description="Kind of BSpecEntity", resource=MusicStorage)
class BSpecEntityKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    A = value(code="a", display_name="A")


@entity(description="Second level", resource=MusicStorage)
class BSpecEntity(BaseSpecEntity):
    """Declare the second level of detail."""

    id: str = Field(description="Identifier")
    back: Annotated[
        Generalization[ASpecEntity],
        Classifier(variant=ASpecEntityKindEnumEntity.B),
        Inverse(ASpecEntity, "detail"),
    ] = Field(description="Return to A")
    detail: Annotated[Specialization[ASpecEntity, BSpecEntityKindEnumEntity], Inverse(field_name="back")] = Field(
        description="Next level"
    )


ASpecEntity.model_rebuild()
BSpecEntity.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
    from aoa.action_machine.graph.validators.entity_specialization_validator import validate_entity_specializations

    try:
        validate_entity_specializations()
    except SpecializationDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The broken declaration was accepted")


if __name__ == "__main__":
    main()
