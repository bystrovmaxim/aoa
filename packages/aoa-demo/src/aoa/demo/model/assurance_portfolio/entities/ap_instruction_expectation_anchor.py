# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_instruction_expectation_anchor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.entities.ap_regulated_expectation_row import (
    AssuranceRegulatedExpectationRowDetailEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_scenario_instruction_line import (
    AssuranceScenarioInstructionLineDetailEntity,
)


@entity(
    description="Trace pin between choreography line and expectation entry (step_has_requirement analogue)",
    domain=AssurancePortfolioDomain,
)
class AssuranceInstructionExpectationAnchorCoreEntity(BaseCoreEntity):
    id: str = Field(description="Trace anchor id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Trace anchor lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    instruction_line: Annotated[
        AssociationOne[AssuranceScenarioInstructionLineDetailEntity],
        NoInverse(),
    ] = Field(
        description="Scenario choreography row"
    )

    expectation_row: Annotated[
        AssociationOne[AssuranceRegulatedExpectationRowDetailEntity],
        NoInverse(),
    ] = Field(
        description="Validated expectation corpus entry"
    )


AssuranceInstructionExpectationAnchorCoreEntity.model_rebuild()
