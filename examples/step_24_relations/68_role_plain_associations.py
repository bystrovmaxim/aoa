"""Plain associations: what cardinality means on each endpoint.
Run: .venv/bin/python examples/step_24_relations/68_role_plain_associations.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, BaseDomain, Inverse
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class AssociationDomain(BaseDomain):
    """Group the plain-association declarations."""

    name = "plain-association"
    description = "Plain associations"


@meta(description="Stores the association entities", domain=AssociationDomain)
class AssociationStorage(BaseStorage):
    """Hold the association entities."""


@entity(description="Customer", resource=AssociationStorage)
class CustomerCoreEntity(BaseCoreEntity):
    """One customer points at one account (AssociationOne / AssociationOne)."""

    id: str = Field(description="Customer identifier")
    account: Annotated[AssociationOne[AccountCoreEntity], Inverse(field_name="customer")] = Field(
        description="Account owned by this customer"
    )


@entity(description="Account", resource=AssociationStorage)
class AccountCoreEntity(BaseCoreEntity):
    """One account points back at one customer."""

    id: str = Field(description="Account identifier")
    customer: Annotated[AssociationOne[CustomerCoreEntity], Inverse(field_name="account")] = Field(
        description="Customer that owns this account"
    )


@entity(description="Team", resource=AssociationStorage)
class TeamCoreEntity(BaseCoreEntity):
    """One team holds many members (AssociationOne / AssociationMany)."""

    id: str = Field(description="Team identifier")
    members: Annotated[AssociationMany[MemberCoreEntity], Inverse(field_name="team")] = Field(
        description="Members of this team"
    )


@entity(description="Member", resource=AssociationStorage)
class MemberCoreEntity(BaseCoreEntity):
    """Many members each belong to one team."""

    id: str = Field(description="Member identifier")
    team: Annotated[AssociationOne[TeamCoreEntity], Inverse(field_name="members")] = Field(
        description="Team this member belongs to"
    )


@entity(description="Group", resource=AssociationStorage)
class GroupCoreEntity(BaseCoreEntity):
    """Many groups share many peer groups (AssociationMany / AssociationMany)."""

    id: str = Field(description="Group identifier")
    peers: Annotated[AssociationMany[PeerCoreEntity], Inverse(field_name="groups")] = Field(description="Peer groups")


@entity(description="Peer", resource=AssociationStorage)
class PeerCoreEntity(BaseCoreEntity):
    """Many peers belong to many groups."""

    id: str = Field(description="Peer identifier")
    groups: Annotated[AssociationMany[GroupCoreEntity], Inverse(field_name="peers")] = Field(
        description="Groups this peer belongs to"
    )


for model in (
    CustomerCoreEntity,
    AccountCoreEntity,
    TeamCoreEntity,
    MemberCoreEntity,
    GroupCoreEntity,
    PeerCoreEntity,
):
    model.model_rebuild()


def main() -> None:
    """Validate the three pairings, then construct one value of each cardinality."""
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

    machine = ActionProductMachine(loggers=[])
    assert machine.graph_coordinator.get_all_nodes()
    assert EntityGraphNode(CustomerCoreEntity).relations[0].properties["cardinality"] == "one"
    assert EntityGraphNode(TeamCoreEntity).relations[0].properties["cardinality"] == "many"
    assert EntityGraphNode(GroupCoreEntity).relations[0].properties["cardinality"] == "many"
    customer = CustomerCoreEntity(id="c1", account=AssociationOne(id="a1"))
    team = TeamCoreEntity(id="t1", members=AssociationMany(ids=("m1", "m2")))
    assert customer.account.id == "a1"
    assert team.members.ids == ("m1", "m2")
    peer = GroupCoreEntity(id="g1", peers=AssociationMany(ids=("p1", "p2")))
    assert peer.peers.ids == ("p1", "p2")
    print("AssociationOne / AssociationOne: accepted")
    print("AssociationOne / AssociationMany: accepted")
    print("AssociationMany / AssociationMany: accepted")
    print("customer.account.id:", customer.account.id)
    print("team.members.ids:", team.members.ids)


if __name__ == "__main__":
    main()
