"""Specialization and generalization pair exclusively.
Run: .venv/bin/python examples/step_21_relations/71_role_specialization.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    EntityFieldDeclarationError,
    Generalization,
    Inverse,
    NoInverse,
    Specialization,
    value,
)
from aoa.action_machine.domain.exceptions import RoleCompatibilityError
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class SpecializationDomain(BaseDomain):
    """Group the specialization declarations."""

    name = "specialization"
    description = "Specialization"


@entity(description="Record kind", domain=SpecializationDomain)
class RecordKindEnumEntity(BaseEnumEntity):
    """The dictionary an axis borrows its codes from."""

    FIRST = value(code="first", display_name="First")


@entity(description="Record", domain=SpecializationDomain)
class RecordCoreEntity(BaseCoreEntity):
    """A head with one classified alternative."""

    id: str = Field(description="Record identifier")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity, RecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Pressing details")


@entity(description="First press", domain=SpecializationDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """The alternative side of the valid axis."""

    id: str = Field(description="Record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(variant=RecordKindEnumEntity.FIRST),
        Inverse(RecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Head with ordinary reverse", domain=SpecializationDomain)
class SpecOrdinaryHeadCoreEntity(BaseCoreEntity):
    """A specialization whose reverse is an ordinary association — refused."""

    id: str = Field(description="Identifier")
    pressing: Annotated[
        Specialization[OrdinaryReverseCoreEntity, RecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Pressing details")


@entity(description="Ordinary reverse", domain=SpecializationDomain)
class OrdinaryReverseCoreEntity(BaseCoreEntity):
    """The reverse is an association, so the specialization / ordinary pair is refused."""

    id: str = Field(description="Identifier")
    record: Annotated[AssociationOne[SpecOrdinaryHeadCoreEntity], Inverse(SpecOrdinaryHeadCoreEntity, "pressing")] = (
        Field(description="Record")
    )


@entity(description="Generalization A", domain=SpecializationDomain)
class GeneralizationACoreEntity(BaseCoreEntity):
    """A generalization whose reverse is another generalization — refused."""

    id: str = Field(description="Identifier")
    b: Annotated[Generalization[GeneralizationBCoreEntity], Inverse(field_name="a")] = Field(
        description="Generalization B"
    )


@entity(description="Generalization B", domain=SpecializationDomain)
class GeneralizationBCoreEntity(BaseCoreEntity):
    """The second generalization of the refused pair."""

    id: str = Field(description="Identifier")
    a: Annotated[Generalization[GeneralizationACoreEntity], Inverse(field_name="b")] = Field(
        description="Generalization A"
    )


@entity(description="Unpaired head", domain=SpecializationDomain)
class UnpairedHeadCoreEntity(BaseCoreEntity):
    """Show that a specialization cannot opt out of its reverse."""

    pressing: Annotated[Specialization[UnpairedDetailSpecEntity, RecordKindEnumEntity], NoInverse()] = Field(
        description="Pressing details"
    )


@entity(description="Detail of unpaired head", domain=SpecializationDomain)
class UnpairedDetailSpecEntity(BaseSpecEntity):
    """Keep the opposite endpoint explicit."""

    record: Annotated[
        Generalization[UnpairedHeadCoreEntity],
        Classifier(variant=RecordKindEnumEntity.FIRST),
        Inverse(field_name="pressing"),
    ] = Field(description="Record")


@entity(description="Unpaired generalization", domain=SpecializationDomain)
class UnpairedAlternativeSpecEntity(BaseSpecEntity):
    """Show that a generalization cannot opt out either."""

    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(variant=RecordKindEnumEntity.FIRST),
        NoInverse(),
    ] = Field(description="Record")


for model in (
    RecordCoreEntity,
    FirstPressSpecEntity,
    UnpairedHeadCoreEntity,
    UnpairedDetailSpecEntity,
    UnpairedAlternativeSpecEntity,
    SpecOrdinaryHeadCoreEntity,
    OrdinaryReverseCoreEntity,
    GeneralizationACoreEntity,
    GeneralizationBCoreEntity,
):
    model.model_rebuild()


def main() -> None:
    """Accept the valid axis, then show the two representative refusals."""
    assert EntityGraphNode(RecordCoreEntity).node_obj is RecordCoreEntity
    detail = FirstPressSpecEntity(id="record-1", stamper="1A", record=Generalization(id="record-1"))
    record = RecordCoreEntity(
        id="record-1", pressing=Specialization(id="record-1", variant=RecordKindEnumEntity.FIRST, entity=detail)
    )
    assert record.pressing.entity is detail
    assert record.pressing.variant is RecordKindEnumEntity.FIRST
    try:
        EntityGraphNode(SpecOrdinaryHeadCoreEntity)
    except RoleCompatibilityError as exc:
        assert (
            str(exc)
            == "Role pair 'Specialization' ↔ 'AssociationOne' is not permitted between 'pressing' on SpecOrdinaryHeadCoreEntity and 'record' on OrdinaryReverseCoreEntity: Specialization and Generalization pair exclusively with each other; declare the reverse endpoint as the matching Specialization or Generalization role."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("The prohibited role pair was accepted")
    try:
        EntityGraphNode(GeneralizationACoreEntity)
    except RoleCompatibilityError as exc:
        assert (
            str(exc)
            == "Role pair 'Generalization' ↔ 'Generalization' is not permitted between 'b' on GeneralizationACoreEntity and 'a' on GeneralizationBCoreEntity: Specialization and Generalization pair exclusively with each other; declare the reverse endpoint as the matching Specialization or Generalization role."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("The prohibited role pair was accepted")
    try:
        EntityGraphNode(UnpairedHeadCoreEntity)
    except EntityFieldDeclarationError as exc:
        assert (
            str(exc)
            == "Field 'pressing' on entity 'UnpairedHeadCoreEntity' is invalid: a specialization/generalization field requires Inverse, never NoInverse; declare a reciprocal Inverse(field_name=...) on both endpoints."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("NoInverse specialization was accepted")
    try:
        EntityGraphNode(UnpairedAlternativeSpecEntity)
    except EntityFieldDeclarationError as exc:
        assert (
            str(exc)
            == "Field 'record' on entity 'UnpairedAlternativeSpecEntity' is invalid: a specialization/generalization field requires Inverse, never NoInverse; declare a reciprocal Inverse(field_name=...) on both endpoints."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("NoInverse generalization was accepted")
    print("Specialization / Generalization: accepted")


if __name__ == "__main__":
    main()
