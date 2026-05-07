# src/maxitor/samples/assurance_portfolio/entities/ap_portfolio_lane_stub.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Broader organizational lane tying multiple workspaces", domain=AssurancePortfolioDomain)
class AssurancePortfolioLaneStubEntity(BaseEntity):
    id: str = Field(description="Portfolio lane id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Lane lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


AssurancePortfolioLaneStubEntity.model_rebuild()
