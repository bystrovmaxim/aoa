# src/maxitor/samples/assurance_portfolio/entities/ap_delegated_work_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorEntity
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceCheckpointToneAxisEntity,
    AssuranceDelegationIntentAxisEntity,
)


@entity(description="Dual-actor delegated assignment with intent + checkpoint hues", domain=AssurancePortfolioDomain)
class AssuranceDelegatedWorkTicketEntity(BaseEntity):
    id: str = Field(description="Delegated ticket id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegated ticket lifecycle")

    assignee_actor: Annotated[
        AssociationOne[AssuranceFacilityActorEntity],
        NoInverse(),
    ] = Rel(description="Actor owed the deliverable")  # type: ignore[assignment]

    delegator_actor: Annotated[
        AssociationOne[AssuranceFacilityActorEntity],
        NoInverse(),
    ] = Rel(description="Actor dispatching workload")  # type: ignore[assignment]

    intent_axis: Annotated[
        AssociationOne[AssuranceDelegationIntentAxisEntity],
        NoInverse(),
    ] = Rel(description="Delegation intent flavour")  # type: ignore[assignment]

    checkpoint_tone: Annotated[
        AssociationOne[AssuranceCheckpointToneAxisEntity],
        NoInverse(),
    ] = Rel(description="Current checkpoint disposition")  # type: ignore[assignment]


AssuranceDelegatedWorkTicketEntity.model_rebuild()
