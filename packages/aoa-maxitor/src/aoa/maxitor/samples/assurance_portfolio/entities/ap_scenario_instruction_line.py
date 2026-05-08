# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_scenario_instruction_line.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.maxitor.samples.assurance_portfolio.entities.ap_scenario_sheet import AssuranceScenarioSheetEntity


@entity(description="Ordered choreography line within scenario sheet (step analogue)", domain=AssurancePortfolioDomain)
class AssuranceScenarioInstructionLineEntity(BaseEntity):
    id: str = Field(description="Instruction line id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Instruction lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    scenario_sheet: Annotated[
        AssociationOne[AssuranceScenarioSheetEntity],
        NoInverse(),
    ] = Rel(description="Parent scenario sheet")  # type: ignore[assignment]


AssuranceScenarioInstructionLineEntity.model_rebuild()
