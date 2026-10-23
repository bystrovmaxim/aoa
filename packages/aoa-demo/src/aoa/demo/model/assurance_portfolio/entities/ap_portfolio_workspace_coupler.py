# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_portfolio_workspace_coupler.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.entities.ap_portfolio_lane_stub import AssurancePortfolioLaneStubCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubCoreEntity,
)


@entity(description="Associative linkage from lane to encapsulated workspace programs", domain=AssurancePortfolioDomain)
class AssurancePortfolioWorkspaceCouplerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Coupler id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Coupler lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    portfolio_lane: Annotated[
        AssociationOne[AssurancePortfolioLaneStubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Owning lane headline"
    )

    workspace_program: Annotated[
        AssociationOne[AssuranceWorkspaceProgramStubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Contained workspace capsule"
    )


AssurancePortfolioWorkspaceCouplerCoreEntity.model_rebuild()
