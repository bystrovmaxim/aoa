# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_delegated_work_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceCheckpointToneAxisCoreEntity,
    AssuranceDelegationIntentAxisCoreEntity,
)


@entity(description="Dual-actor delegated assignment with intent + checkpoint hues", domain=AssurancePortfolioDomain)
class AssuranceDelegatedWorkTicketCoreEntity(BaseCoreEntity):
    id: str = Field(description="Delegated ticket id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegated ticket lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    assignee_actor: Annotated[
        AssociationOne[AssuranceFacilityActorCoreEntity],
        NoInverse(),
    ] = Field(
        description="Actor owed the deliverable"
    )

    delegator_actor: Annotated[
        AssociationOne[AssuranceFacilityActorCoreEntity],
        NoInverse(),
    ] = Field(
        description="Actor dispatching workload"
    )

    intent_axis: Annotated[
        AssociationOne[AssuranceDelegationIntentAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Delegation intent flavour"
    )

    checkpoint_tone: Annotated[
        AssociationOne[AssuranceCheckpointToneAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Current checkpoint disposition"
    )


AssuranceDelegatedWorkTicketCoreEntity.model_rebuild()
