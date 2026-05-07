# src/maxitor/samples/assurance_portfolio/entities/ap_campaign_wave_banner.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Execution wave façade (test_plan analogue)", domain=AssurancePortfolioDomain)
class AssuranceCampaignWaveBannerEntity(BaseEntity):
    id: str = Field(description="Campaign wave id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Wave lifecycle")


AssuranceCampaignWaveBannerEntity.model_rebuild()
