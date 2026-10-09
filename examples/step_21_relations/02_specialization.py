"""
02_specialization.py — Entity specialization: one head field, N extension tables

A head row often continues in one of several tables, and which one depends on a
value the row itself carries: an event is created, updated, deleted, moved or
assigned, and each of those has its own table with its own columns. Relations as
chapter 21 describes them cannot say this — a field's target type is exactly one,
whichever container is chosen.

Specialization declares it. The head names its alternatives, each with the code
that selects it, and the classifier field whose value chooses:

    details: Annotated[
        Specialization(CreatedEventEntity, classifier="created_event"),
        ...
        Inverse(field_name="event"),
        By("event_type"),
    ] = Rel(description="...")

Every extension declares the way back, repeating its own code:

    event: Annotated[
        Generalization(EventEntity, classifier="created_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="...")

The code is declared on both sides and the build compares them — neither side is
the authority, the match is. A head may carry several axes over the same set of
extensions (here `event_type` and `channel`), while each extension has exactly
one head.

Tutorial: ../../docs/tutorials/step-21-relations.md  ·  topic: Entity specialization

Run:
    uv run python examples/step_21_relations/02_specialization.py
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, get_args

from pydantic import Field
from typing_extensions import get_type_hints

from aoa.action_machine.domain import (
    AssociationOne,
    BaseEntity,
    By,
    Generalization,
    Inverse,
    Rel,
    RelationNotLoadedError,
    Specialization,
    SpecializationDeclarationError,
    SpecializationOne,
    UndeclaredSpecializationVariantError,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class EventsDomain(BaseDomain):
    name = "events"
    description = "Event log domain"


# ─────────────────────────────────────────────────────────────────────────────
# The extensions. Each holds the continuation of an event row, has its own
# columns, and declares its own code beside the reverse field.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="Event created", domain=EventsDomain)
class CreatedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    actor: str = Field(description="Who created the event")
    source: str = Field(description="Originating system")

    event: Annotated[
        Generalization(EventEntity, classifier="created_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")

    origin_event: Annotated[
        Generalization(EventEntity, classifier="web"),
        Inverse(EventEntity, "origin"),
    ] = Rel(description="Event this extension belongs to, along the channel axis")


@entity(description="Event updated", domain=EventsDomain)
class UpdatedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    actor: str = Field(description="Who updated the event")
    changed_fields: str = Field(description="Comma-separated names of changed fields")

    event: Annotated[
        Generalization(EventEntity, classifier="updated_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")

    origin_event: Annotated[
        Generalization(EventEntity, classifier="mobile"),
        Inverse(EventEntity, "origin"),
    ] = Rel(description="Event this extension belongs to, along the channel axis")


@entity(description="Event deleted", domain=EventsDomain)
class DeletedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    reason: str = Field(description="Why the event was deleted")
    soft: bool = Field(description="True when the row is only marked deleted")

    event: Annotated[
        Generalization(EventEntity, classifier="deleted_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")

    origin_event: Annotated[
        Generalization(EventEntity, classifier="batch"),
        Inverse(EventEntity, "origin"),
    ] = Rel(description="Event this extension belongs to, along the channel axis")


@entity(description="Event moved", domain=EventsDomain)
class MovedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    from_stage: str = Field(description="Stage the event left")
    to_stage: str = Field(description="Stage the event entered")

    event: Annotated[
        Generalization(EventEntity, classifier="moved_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")

    origin_event: Annotated[
        Generalization(EventEntity, classifier="web"),
        Inverse(EventEntity, "origin"),
    ] = Rel(description="Event this extension belongs to, along the channel axis")


@entity(description="Event assigned", domain=EventsDomain)
class AssignedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    assignee: str = Field(description="Who the event was assigned to")
    team: str = Field(description="Team the assignee belongs to")

    event: Annotated[
        Generalization(EventEntity, classifier="assigned_event"),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")

    origin_event: Annotated[
        Generalization(EventEntity, classifier="mobile"),
        Inverse(EventEntity, "origin"),
    ] = Rel(description="Event this extension belongs to, along the channel axis")


# ─────────────────────────────────────────────────────────────────────────────
# The head. One field per axis, both axes over the same five extensions.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="Event", domain=EventsDomain)
class EventEntity(BaseEntity):
    id: str = Field(description="Event id")
    event_date: date = Field(description="When the event happened")
    event_type: str = Field(description="Classifier: which extension table holds the details")
    channel: str = Field(description="Classifier: where the event came from")

    details: Annotated[
        Specialization(CreatedEventEntity, classifier="created_event"),
        Specialization(UpdatedEventEntity, classifier="updated_event"),
        Specialization(DeletedEventEntity, classifier="deleted_event"),
        Specialization(MovedEventEntity, classifier="moved_event"),
        Specialization(AssignedEventEntity, classifier="assigned_event"),
        Inverse(field_name="event"),
        By("event_type"),
    ] = Rel(description="Event details: one of the declared extensions")

    origin: Annotated[
        Specialization(CreatedEventEntity, classifier="web"),
        Specialization(UpdatedEventEntity, classifier="mobile"),
        Specialization(DeletedEventEntity, classifier="batch"),
        Specialization(MovedEventEntity, classifier="web"),
        Specialization(AssignedEventEntity, classifier="mobile"),
        Inverse(field_name="origin_event"),
        By("channel"),
    ] = Rel(description="Where the event came from: the same five extensions")


for _cls in (
    CreatedEventEntity,
    UpdatedEventEntity,
    DeletedEventEntity,
    MovedEventEntity,
    AssignedEventEntity,
    EventEntity,
):
    _cls.model_rebuild()


# ─────────────────────────────────────────────────────────────────────────────
# A deliberately broken model. `assigned` on the extension is not the code the
# head declares for it (`assigned_event`), and a code that disagrees on the two
# sides is a build error naming both of them — not a field that quietly points at
# the wrong table. Section 6 below shows that failure. Remove this class and the
# file describes a model that builds.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="Event assigned (a code that disagrees with the head)", domain=EventsDomain)
class BrokenAssignedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the event row")
    assignee: str = Field(description="Who the event was assigned to")

    event: Annotated[
        Generalization(BrokenEventEntity, classifier="assigned"),  # the head says "assigned_event"
        Inverse(BrokenEventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")


@entity(description="Event (the head of the broken pair)", domain=EventsDomain)
class BrokenEventEntity(BaseEntity):
    id: str = Field(description="Event id")
    event_type: str = Field(description="Classifier: which extension table holds the details")

    details: Annotated[
        Specialization(BrokenAssignedEventEntity, classifier="assigned_event"),
        Inverse(field_name="event"),
        By("event_type"),
    ] = Rel(description="Event details: one of the declared extensions")


BrokenAssignedEventEntity.model_rebuild()
BrokenEventEntity.model_rebuild()


@entity(description="Event (a head field declared beside an ownership container)", domain=EventsDomain)
class BrokenContainerHeadEntity(BaseEntity):
    id: str = Field(description="Event id")
    event_type: str = Field(description="Classifier: which extension table holds the details")

    # Both readings are available and neither is right: the container names one
    # target, the markers name five. The declaration is refused, not guessed.
    details: Annotated[
        AssociationOne[CreatedEventEntity],
        Specialization(CreatedEventEntity, classifier="created_event"),
        Inverse(field_name="event"),
        By("event_type"),
    ] = Rel(description="Ambiguous: a container and alternatives in one field")


BrokenContainerHeadEntity.model_rebuild()


def declared_axes(head_cls: type[BaseEntity]) -> list[tuple[str, str, tuple[tuple[str, type[BaseEntity]], ...]]]:
    """Return, per axis: the field name, its classifier field, and (code, alternative) pairs."""
    hints = get_type_hints(head_cls, include_extras=True)
    axes: list[tuple[str, str, tuple[tuple[str, type[BaseEntity]], ...]]] = []
    for field_name in head_cls.model_fields:
        metadata = get_args(hints[field_name])[1:]
        alternatives = tuple((item.classifier, item.target_entity) for item in metadata if isinstance(item, Specialization))
        if not alternatives:
            continue
        classifier = next((item.field_name for item in metadata if isinstance(item, By)), "")
        axes.append((field_name, classifier, alternatives))
    return axes


def main() -> None:
    # 1) The model is the specification. Building the machine builds the graph,
    #    and the graph is where every declaration rule is checked: the codes on
    #    both sides match, every alternative carries a partner field, no class is
    #    claimed by two heads. A broken declaration raises here, at startup.
    ActionProductMachine()
    print("1) Machine built — the specialization declaration was accepted")

    # 2) What the head's field says: N alternatives with their codes, one per axis.
    print("\n2) The declared axes:")
    for field_name, classifier, alternatives in declared_axes(EventEntity):
        print(f"   {field_name}: chosen by `{classifier}`, {len(alternatives)} alternatives")
        for code, target in alternatives:
            print(f"      {code:<16} -> {target.__name__}")

    # 3) The value the field holds. The id says which row, the variant says which
    #    table — with an un-hydrated row there is otherwise no way to tell.
    axis = "details"
    details = SpecializationOne(id="evt-1", variant="created_event", axis=axis)
    print("\n3) An id-only value:")
    print(f"   details.id = {details.id}   details.variant = {details.variant}   is_loaded={details.is_loaded}")
    try:
        _ = details.actor
    except RelationNotLoadedError as exc:
        print(f"   details.actor -> {type(exc).__name__}: {exc}")

    # 4) A code that no alternative declares is an explicit failure at the moment
    #    the value is built — never "no relation", which would hide a data defect.
    try:
        SpecializationOne(id="evt-2", variant="archived_event", axis=axis)
    except Exception as exc:  # noqa: BLE001 — the reader is meant to see whatever the framework raises
        print(f"\n4) A code nobody declared -> {type(exc).__name__}: {exc}")

    # 5) Hydrated with the wrong table is caught just as early: the class must be
    #    the one declared for the code, or the answer would be confidently wrong.
    try:
        SpecializationOne(
            id="evt-3",
            variant="created_event",
            axis=axis,
            entity=DeletedEventEntity(id="evt-3", reason="oops", soft=True),
        )
    except Exception as exc:  # noqa: BLE001 — the reader is meant to see whatever the framework raises
        print(f"\n5) The wrong table hydrated -> {type(exc).__name__}: {exc}")

    # 6) A declaration that disagrees with itself fails at build, naming both
    #    sides. `BrokenAssignedEventEntity` says `assigned` where its head says
    #    `assigned_event`; the build compares the two codes and refuses to guess.
    try:
        ActionProductMachine()
    except SpecializationDeclarationError as exc:
        print(f"\n6) A code that disagrees -> {type(exc).__name__}: {exc}")

    # The second spelling a broken model takes: a head field declared next to an
    # ownership container. The annotation is refused rather than resolved to one
    # of the two readings — see `AssociationOne` in the line above.
    try:
        _ = BrokenContainerHeadEntity.model_rebuild()
        ActionProductMachine()
    except Exception as exc:  # noqa: BLE001 — the reader is meant to see whatever the framework raises
        print(f"\n7) Markers beside an ownership container -> {type(exc).__name__}: {exc}")

    print(
        "\nSummary: one head field, five extension tables, one classifier choosing among them. "
        "\nFirst the good model builds; then the broken one is refused, which is the point: "
        "\na relation that points at the wrong table would otherwise never be noticed."
    )


if __name__ == "__main__":
    main()
