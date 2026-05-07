# src/maxitor/samples/assurance_portfolio/entities/ap_workspace_program_stub.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Primary assurance workspace capsule (test_project analogue)", domain=AssurancePortfolioDomain)
class AssuranceWorkspaceProgramStubEntity(BaseEntity):
    id: str = Field(description="Workspace program id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Workspace lifecycle")


AssuranceWorkspaceProgramStubEntity.model_rebuild()
