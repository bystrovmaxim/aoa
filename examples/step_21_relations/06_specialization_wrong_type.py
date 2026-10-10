"""Rejecting an unrelated object.

Does the container accept a record where pressing details are required?
Run from the repository root:
    uv run python examples/step_21_relations/06_specialization_wrong_type.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="Pressing identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="Pressing identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="Pressing identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordEntity, FirstPressEntity, RepressEntity, TestPressEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    from pydantic import ValidationError

    record = VinylRecordEntity(
        id="rec-1",
        title="Kind of Blue",
        media="first",
        pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="press-1",
            variant="first",
        ),
    )
    try:
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="press-1",
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
