"""Aggregation: shared ownership pairs only with an association.
Run: .venv/bin/python examples/step_21_relations/69_role_aggregation.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    Inverse,
)
from aoa.action_machine.domain.exceptions import RoleCompatibilityError
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class AggregationDomain(BaseDomain):
    """Group the aggregation declarations."""

    name = "aggregation"
    description = "Aggregation"


@entity(description="Team", domain=AggregationDomain)
class TeamCoreEntity(BaseCoreEntity):
    """A team aggregates one lead; the lead keeps its own lifecycle."""

    id: str = Field(description="Team identifier")
    lead: Annotated[AggregateOne[LeadCoreEntity], Inverse(field_name="leads")] = Field(description="Team lead")


@entity(description="Lead", domain=AggregationDomain)
class LeadCoreEntity(BaseCoreEntity):
    """A lead's reverse endpoint is an association, never another aggregate."""

    id: str = Field(description="Lead identifier")
    leads: Annotated[AssociationMany[TeamCoreEntity], Inverse(field_name="lead")] = Field(
        description="Teams this lead guides"
    )


@entity(description="Department", domain=AggregationDomain)
class DepartmentCoreEntity(BaseCoreEntity):
    """A department aggregates many members."""

    id: str = Field(description="Department identifier")
    members: Annotated[AggregateMany[StaffCoreEntity], Inverse(field_name="department")] = Field(
        description="Department members"
    )


@entity(description="Staff", domain=AggregationDomain)
class StaffCoreEntity(BaseCoreEntity):
    """A staff member points back through an association."""

    id: str = Field(description="Staff identifier")
    department: Annotated[AssociationOne[DepartmentCoreEntity], Inverse(field_name="members")] = Field(
        description="Department of this staff member"
    )


@entity(description="Aggregate A", domain=AggregationDomain)
class AggregateACoreEntity(BaseCoreEntity):
    """An aggregate whose reverse is another aggregate — refused."""

    id: str = Field(description="Identifier")
    b: Annotated[AggregateOne[AggregateBCoreEntity], Inverse(field_name="a")] = Field(description="Aggregate B")


@entity(description="Aggregate B", domain=AggregationDomain)
class AggregateBCoreEntity(BaseCoreEntity):
    """The second aggregate of the refused pair."""

    id: str = Field(description="Identifier")
    a: Annotated[AggregateOne[AggregateACoreEntity], Inverse(field_name="b")] = Field(description="Aggregate A")


@entity(description="Corrected aggregate", domain=AggregationDomain)
class CorrectedAggregateCoreEntity(BaseCoreEntity):
    """The corrected pair keeps one aggregate and one association."""

    id: str = Field(description="Identifier")
    b: Annotated[AggregateOne[CorrectedReverseCoreEntity], Inverse(field_name="a")] = Field(description="Reverse")


@entity(description="Corrected reverse", domain=AggregationDomain)
class CorrectedReverseCoreEntity(BaseCoreEntity):
    """The reverse is an association, so the pair is permitted."""

    id: str = Field(description="Identifier")
    a: Annotated[AssociationOne[CorrectedAggregateCoreEntity], Inverse(field_name="b")] = Field(description="Aggregate")


for model in (
    TeamCoreEntity,
    LeadCoreEntity,
    DepartmentCoreEntity,
    StaffCoreEntity,
    AggregateACoreEntity,
    AggregateBCoreEntity,
    CorrectedAggregateCoreEntity,
    CorrectedReverseCoreEntity,
):
    model.model_rebuild()


def main() -> None:
    """Show the two permitted pairs, the refused aggregate pair and its correction."""
    assert EntityGraphNode(TeamCoreEntity).relations[0].properties["cardinality"] == "one"
    assert EntityGraphNode(DepartmentCoreEntity).relations[0].properties["cardinality"] == "many"
    assert EntityGraphNode(CorrectedAggregateCoreEntity).node_obj is CorrectedAggregateCoreEntity
    lead = TeamCoreEntity(id="team-1", lead=AggregateOne(id="lead-1"))
    staff = DepartmentCoreEntity(id="department-1", members=AggregateMany(ids=("staff-1",)))
    assert lead.lead.id == "lead-1"
    assert staff.members.ids == ("staff-1",)
    try:
        EntityGraphNode(AggregateACoreEntity)
    except RoleCompatibilityError as exc:
        assert (
            str(exc)
            == "Role pair 'AggregateOne' ↔ 'AggregateOne' is not permitted between 'b' on AggregateACoreEntity and 'a' on AggregateBCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("The prohibited role pair was accepted")
    print("AggregateOne / AssociationMany: accepted")
    print("AggregateMany / AssociationOne: accepted")
    print("AggregateOne / AssociationOne: accepted")


if __name__ == "__main__":
    main()
