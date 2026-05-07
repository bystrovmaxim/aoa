# src/maxitor/samples/assurance_portfolio/entities/ap_instruction_expectation_anchor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_regulated_expectation_row import (
    AssuranceRegulatedExpectationRowEntity,
)
from maxitor.samples.assurance_portfolio.entities.ap_scenario_instruction_line import (
    AssuranceScenarioInstructionLineEntity,
)


@entity(
    description="Trace pin between choreography line and expectation entry (step_has_requirement analogue)",
    domain=AssurancePortfolioDomain,
)
class AssuranceInstructionExpectationAnchorEntity(BaseEntity):
    id: str = Field(description="Trace anchor id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Trace anchor lifecycle")

    instruction_line: Annotated[
        AssociationOne[AssuranceScenarioInstructionLineEntity],
        NoInverse(),
    ] = Rel(description="Scenario choreography row")  # type: ignore[assignment]

    expectation_row: Annotated[
        AssociationOne[AssuranceRegulatedExpectationRowEntity],
        NoInverse(),
    ] = Rel(description="Validated expectation corpus entry")  # type: ignore[assignment]


AssuranceInstructionExpectationAnchorEntity.model_rebuild()
