# src/maxitor/samples/assurance_portfolio/entities/ap_expectation_catalog_stub.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Expectation bucket container (requirement_spec analogue)", domain=AssurancePortfolioDomain)
class AssuranceExpectationCatalogStubEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Catalog lifecycle")
    id: str = Field(description="Expectation catalog id")


AssuranceExpectationCatalogStubEntity.model_rebuild()
