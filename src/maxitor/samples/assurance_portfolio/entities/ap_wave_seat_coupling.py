# src/maxitor/samples/assurance_portfolio/entities/ap_wave_seat_coupling.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_campaign_wave_banner import (
    AssuranceCampaignWaveBannerEntity,
)
from maxitor.samples.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorEntity
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Actor ↔ execution wave duty binding (plan role analogue)", domain=AssurancePortfolioDomain)
class AssuranceWaveSeatCouplingEntity(BaseEntity):
    id: str = Field(description="Wave seat coupling id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Wave seat coupling lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    actor: Annotated[
        AssociationOne[AssuranceFacilityActorEntity],
        NoInverse(),
    ] = Rel(description="Duty-bound actor")  # type: ignore[assignment]

    campaign_wave: Annotated[
        AssociationOne[AssuranceCampaignWaveBannerEntity],
        NoInverse(),
    ] = Rel(description="Subject wave banner")  # type: ignore[assignment]


AssuranceWaveSeatCouplingEntity.model_rebuild()
