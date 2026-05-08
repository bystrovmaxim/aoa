# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_expectation_catalog_stub.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Expectation bucket container (requirement_spec analogue)", domain=AssurancePortfolioDomain)
class AssuranceExpectationCatalogStubEntity(BaseEntity):
    id: str = Field(description="Expectation catalog id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Catalog lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


AssuranceExpectationCatalogStubEntity.model_rebuild()
