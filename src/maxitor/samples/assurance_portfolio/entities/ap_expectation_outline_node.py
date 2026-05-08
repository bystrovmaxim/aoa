# src/maxitor/samples/assurance_portfolio/entities/ap_expectation_outline_node.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_expectation_catalog_stub import (
    AssuranceExpectationCatalogStubEntity,
)
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceSpecificationDepthAxisEntity,
)


@entity(
    description="Hierarchical outline row without self edges (requirement_spec_node analogue)",
    domain=AssurancePortfolioDomain,
)
class AssuranceExpectationOutlineNodeEntity(BaseEntity):
    id: str = Field(description="Outline node id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Outline node lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    catalog_bucket: Annotated[
        AssociationOne[AssuranceExpectationCatalogStubEntity],
        NoInverse(),
    ] = Rel(description="Parent catalog capsule")  # type: ignore[assignment]

    depth_axis: Annotated[
        AssociationOne[AssuranceSpecificationDepthAxisEntity],
        NoInverse(),
    ] = Rel(description="Depth posture on catalog spine")  # type: ignore[assignment]


AssuranceExpectationOutlineNodeEntity.model_rebuild()
