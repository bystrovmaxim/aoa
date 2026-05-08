# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_scenario_sheet.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.maxitor.samples.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubEntity,
)


@entity(description="Scenario blueprint bound to workspace (test_case analogue)", domain=AssurancePortfolioDomain)
class AssuranceScenarioSheetEntity(BaseEntity):
    id: str = Field(description="Scenario sheet id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Scenario lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    workspace_program: Annotated[
        AssociationOne[AssuranceWorkspaceProgramStubEntity],
        NoInverse(),
    ] = Rel(description="Owning assurance workspace")  # type: ignore[assignment]


AssuranceScenarioSheetEntity.model_rebuild()
