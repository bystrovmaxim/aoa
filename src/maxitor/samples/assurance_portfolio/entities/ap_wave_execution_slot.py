# src/maxitor/samples/assurance_portfolio/entities/ap_wave_execution_slot.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_campaign_wave_banner import (
    AssuranceCampaignWaveBannerEntity,
)
from maxitor.samples.assurance_portfolio.entities.ap_execution_attempt_ticket import (
    AssuranceExecutionAttemptTicketEntity,
)
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Associative scheduling link between waves and executions (plan_has_test analogue)", domain=AssurancePortfolioDomain)
class AssuranceWaveExecutionSlotEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Slot lifecycle")
    id: str = Field(description="Wave execution slot id")

    campaign_wave: Annotated[
        AssociationOne[AssuranceCampaignWaveBannerEntity],
        NoInverse(),
    ] = Rel(description="Scheduling banner")  # type: ignore[assignment]

    execution_attempt: Annotated[
        AssociationOne[AssuranceExecutionAttemptTicketEntity],
        NoInverse(),
    ] = Rel(description="Mounted execution candidate")  # type: ignore[assignment]


AssuranceWaveExecutionSlotEntity.model_rebuild()
