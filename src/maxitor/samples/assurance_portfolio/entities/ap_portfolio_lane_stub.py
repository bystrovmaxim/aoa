# src/maxitor/samples/assurance_portfolio/entities/ap_portfolio_lane_stub.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Broader organizational lane tying multiple workspaces", domain=AssurancePortfolioDomain)
class AssurancePortfolioLaneStubEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Lane lifecycle")
    id: str = Field(description="Portfolio lane id")


AssurancePortfolioLaneStubEntity.model_rebuild()
