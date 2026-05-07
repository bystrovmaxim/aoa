# src/maxitor/samples/assurance_portfolio/entities/ap_scenario_instruction_line.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_scenario_sheet import AssuranceScenarioSheetEntity


@entity(description="Ordered choreography line within scenario sheet (step analogue)", domain=AssurancePortfolioDomain)
class AssuranceScenarioInstructionLineEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Instruction lifecycle")
    id: str = Field(description="Instruction line id")

    scenario_sheet: Annotated[
        AssociationOne[AssuranceScenarioSheetEntity],
        NoInverse(),
    ] = Rel(description="Parent scenario sheet")  # type: ignore[assignment]


AssuranceScenarioInstructionLineEntity.model_rebuild()
