"""Specialization requires both type arguments.

Try the retired one-argument container form.
Run: uv run python examples/step_24_relations/50_error_one_argument.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
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


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@meta(description="Stores the music entities", domain=MusicDomain)
class MusicStorage(BaseStorage):
    """Hold the music entities."""


@entity(description="Kind of VinylRecordCoreEntity", resource=MusicStorage)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    FIRST = value(code="first", display_name="First")
    REPRESS = value(code="repress", display_name="Repress")
    TEST = value(code="test", display_name="Test")


@entity(description="Vinyl record", resource=MusicStorage)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Details of this pressing")


@entity(description="First pressing", resource=MusicStorage)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Re-pressing", resource=MusicStorage)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.REPRESS),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Test pressing", resource=MusicStorage)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.TEST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    try:
        Specialization[FirstPressSpecEntity | RepressSpecEntity]
    except TypeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A container without a dictionary was accepted")


if __name__ == "__main__":
    main()
