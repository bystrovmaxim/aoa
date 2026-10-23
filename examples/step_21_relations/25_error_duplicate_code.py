"""Two alternatives cannot share one value.

Give two alternative classes the same dictionary value.
Run: uv run python examples/step_21_relations/25_error_duplicate_code.py
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


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Kind of VinylRecordCoreEntity", domain=MusicDomain)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    FIRST = value(code="first", display_name="First")
    REPRESS = value(code="repress", display_name="Repress")


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.REPRESS),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()


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
