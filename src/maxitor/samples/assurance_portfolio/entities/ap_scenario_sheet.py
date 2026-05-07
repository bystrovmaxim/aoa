# src/maxitor/samples/assurance_portfolio/entities/ap_scenario_sheet.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubEntity,
)


@entity(description="Scenario blueprint bound to workspace (test_case analogue)", domain=AssurancePortfolioDomain)
class AssuranceScenarioSheetEntity(BaseEntity):
    id: str = Field(description="Scenario sheet id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Scenario lifecycle")

    workspace_program: Annotated[
        AssociationOne[AssuranceWorkspaceProgramStubEntity],
        NoInverse(),
    ] = Rel(description="Owning assurance workspace")  # type: ignore[assignment]


AssuranceScenarioSheetEntity.model_rebuild()
