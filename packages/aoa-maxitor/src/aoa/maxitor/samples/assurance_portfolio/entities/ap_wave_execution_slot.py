# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_wave_execution_slot.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_campaign_wave_banner import (
    AssuranceCampaignWaveBannerEntity,
)
from aoa.maxitor.samples.assurance_portfolio.entities.ap_execution_attempt_ticket import (
    AssuranceExecutionAttemptTicketEntity,
)
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Associative scheduling link between waves and executions (plan_has_test analogue)", domain=AssurancePortfolioDomain)
class AssuranceWaveExecutionSlotEntity(BaseEntity):
    id: str = Field(description="Wave execution slot id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Slot lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    campaign_wave: Annotated[
        AssociationOne[AssuranceCampaignWaveBannerEntity],
        NoInverse(),
    ] = Rel(description="Scheduling banner")  # type: ignore[assignment]

    execution_attempt: Annotated[
        AssociationOne[AssuranceExecutionAttemptTicketEntity],
        NoInverse(),
    ] = Rel(description="Mounted execution candidate")  # type: ignore[assignment]


AssuranceWaveExecutionSlotEntity.model_rebuild()
