# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_delegated_work_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorEntity
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.maxitor.samples.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceCheckpointToneAxisEntity,
    AssuranceDelegationIntentAxisEntity,
)


@entity(description="Dual-actor delegated assignment with intent + checkpoint hues", domain=AssurancePortfolioDomain)
class AssuranceDelegatedWorkTicketEntity(BaseEntity):
    id: str = Field(description="Delegated ticket id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegated ticket lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
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
