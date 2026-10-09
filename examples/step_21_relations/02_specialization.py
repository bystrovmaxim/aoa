"""
02_specialization.py — Entity specialization: one head field, N extension tables

A head row often continues in one of several tables, and which one depends on a value
the row itself carries: an event is created, updated, deleted, moved or assigned, and
each of those has its own table with its own columns. A relation as chapter 21 describes
it cannot say this — a field's target type is exactly one, whichever container is chosen.

Specialization declares it. The head's field is parameterised by the union of its
alternatives, and a marker names the field that chooses among them:

    pressed: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", variants=Literal["first", "repress", "test"]),
        Inverse(FirstPressEntity, "record"),
    ] = Rel(description="How this record was pressed")

Every extension declares the way back, with its own code:

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")

Both containers are pydantic models, so subscripting one gives a real class: the type
argument is what pydantic validates, and a class the union does not list is refused.
The value carries the identifier, which variant it is, and the hydrated row when one
was loaded — so an id-only link is expressible, and reading a link tells you which
table to go to.

Tutorial: ../../docs/tutorials/step-21-relations.md  ·  topic: Entity specialization

Run:
    uv run python examples/step_21_relations/02_specialization.py
"""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class MusicDomain(BaseDomain):
    name = "music"
    description = "A music library"


# ─────────────────────────────────────────────────────────────────────────────
# The extensions. Each holds the continuation of a record row, has its own
# columns, and declares its own code beside the reverse link.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    stamper: str = Field(description="Stamper code")
    year: int = Field(description="Year of the first press")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    year: int = Field(description="Year of the re-press")
    remastered: bool = Field(description="Whether the audio was remastered")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    approved_by: str = Field(description="Who signed it off")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


# ─────────────────────────────────────────────────────────────────────────────
# The head. One field, parameterised by the union of its alternatives; the
# codes are declared in the same order as the alternatives are written.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    id: str = Field(description="Record id")
    title: str = Field(description="Album title")
    media: str = Field(description="Classifier: which pressing this is")

    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", variants=Literal["first", "repress", "test"]),
        Inverse(FirstPressEntity, "record"),
    ] = Rel(description="How this record was pressed")


for _cls in (FirstPressEntity, RepressEntity, TestPressEntity, VinylRecordEntity):
    _cls.model_rebuild()


def declared_alternatives() -> tuple[type[BaseEntity], ...]:
    """Return the classes the head's field was parameterised by."""
    annotation = VinylRecordEntity.model_fields["pressing"].annotation
    return tuple(get_args(annotation.__pydantic_generic_metadata__["args"][0]))


def declared_classifier() -> Classifier | None:
    """Return the classifier marker of the head's field, if it declares one."""
    for item in VinylRecordEntity.model_fields["pressing"].metadata:
        if isinstance(item, Classifier):
            return item
    return None


def main() -> None:
    # 1) What the head declares: the alternatives and the codes they answer to.
    marker = declared_classifier()
    print("1) The declaration:")
    print("   alternatives:", [c.__name__ for c in declared_alternatives()])
    print("   chosen by   :", marker.field if marker else "?")
    print("   codes       :", list(marker.codes) if marker else [])

    # 2) Writing a link, reading it back. The value carries the id, the variant
    #    and — when the row was loaded — the row itself.
    first = FirstPressEntity(id="rec-1", stamper="1A", year=1959)
    record = VinylRecordEntity(
        id="rec-1",
        title="Kind of Blue",
        media="first",
        pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="rec-1",
            variant="first",
            entity=first,
        ),
    )
    print()
    print("2) A hydrated link:")
    print("   pressing         =", record.pressing)
    print("   .variant         =", record.pressing.variant)
    print("   .entity          =", type(record.pressing.entity).__name__)
    print("   .entity.stamper  =", record.pressing.entity.stamper)

    # 3) The same field, another alternative — same entity class, other table.
    repress = RepressEntity(id="rec-2", year=1997, remastered=True)
    other = VinylRecordEntity(
        id="rec-2",
        title="Kind of Blue",
        media="repress",
        pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="rec-2",
            variant="repress",
            entity=repress,
        ),
    )
    print()
    print("3) Another alternative in the same field:")
    print("   .variant =", other.pressing.variant, "| .entity =", type(other.pressing.entity).__name__)

    # 4) Reading the variant you got — plain isinstance, no framework call.
    print()
    print("4) What each row holds:")
    for item in (record, other):
        linked = item.pressing.entity
        if isinstance(linked, FirstPressEntity):
            print(f"   {item.id}: first press, stamper {linked.stamper}")
        elif isinstance(linked, RepressEntity):
            print(f"   {item.id}: repress from {linked.year}, remastered={linked.remastered}")
        else:
            print(f"   {item.id}: another pressing")

    # 5) A link whose row is not loaded: the id and the variant are still there.
    print()
    print("5) A link without a loaded row:")
    unloaded = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](id="rec-3", variant="test")
    print("   built:", unloaded, "| .entity:", unloaded.entity)

    # 6) The type argument is what the model enforces.
    print()
    print("6) What the model refuses:")
    for label, value in (
        ("a string instead of a row", "not an entity"),
        ("a class outside the union", VinylRecordEntity(id="rec-9", title="Other", media="first")),
    ):
        try:
            Specialization[FirstPressEntity | RepressEntity | TestPressEntity](id="x", variant="v", entity=value)
            print(f"   {label:28} -> accepted")
        except ValidationError:
            print(f"   {label:28} -> refused")


if __name__ == "__main__":
    main()
