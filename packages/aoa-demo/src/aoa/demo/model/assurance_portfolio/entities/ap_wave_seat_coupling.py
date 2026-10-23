# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_wave_seat_coupling.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_campaign_wave_banner import AssuranceCampaignWaveBannerCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Actor ↔ execution wave duty binding (plan role analogue)", domain=AssurancePortfolioDomain)
class AssuranceWaveSeatCouplingCoreEntity(BaseCoreEntity):
    id: str = Field(description="Wave seat coupling id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Wave seat coupling lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    actor: Annotated[
        AssociationOne[AssuranceFacilityActorCoreEntity],
        NoInverse(),
    ] = Field(
        description="Duty-bound actor"
    )

    campaign_wave: Annotated[
        AssociationOne[AssuranceCampaignWaveBannerCoreEntity],
        NoInverse(),
    ] = Field(
        description="Subject wave banner"
    )


AssuranceWaveSeatCouplingCoreEntity.model_rebuild()
