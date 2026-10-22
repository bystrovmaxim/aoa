"""Rejecting an unrelated object.

Does the container accept a record where pressing details are required?
Run from the repository root:
    uv run python examples/step_21_relations/06_specialization_wrong_type.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    from pydantic import ValidationError

    record = VinylRecordCoreEntity(
        id="rec-1",
        title="Kind of Blue",
        media="first",
        pressing=Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity](
            id="rec-1",
            variant="first",
        ),
    )
    try:
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity](
            id="rec-1",
            variant="first",
            entity=record,
        )
    except ValidationError as error:
        print(type(error).__name__)
        print(sorted({item["type"] for item in error.errors()}))
    else:
        raise AssertionError("An unrelated entity was accepted")


if __name__ == "__main__":
    main()
