# src/maxitor/samples/assurance_portfolio/entities/ap_portfolio_workspace_coupler.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_portfolio_lane_stub import AssurancePortfolioLaneStubEntity
from maxitor.samples.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubEntity,
)


@entity(description="Associative linkage from lane to encapsulated workspace programs", domain=AssurancePortfolioDomain)
class AssurancePortfolioWorkspaceCouplerEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Coupler lifecycle")
    id: str = Field(description="Coupler id")

    portfolio_lane: Annotated[
        AssociationOne[AssurancePortfolioLaneStubEntity],
        NoInverse(),
    ] = Rel(description="Owning lane headline")  # type: ignore[assignment]

    workspace_program: Annotated[
        AssociationOne[AssuranceWorkspaceProgramStubEntity],
        NoInverse(),
    ] = Rel(description="Contained workspace capsule")  # type: ignore[assignment]


AssurancePortfolioWorkspaceCouplerEntity.model_rebuild()
