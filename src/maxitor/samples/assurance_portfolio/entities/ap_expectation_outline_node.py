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
    lifecycle: AssurancePortfolioLifecycle = Field(description="Outline node lifecycle")
    id: str = Field(description="Outline node id")

    catalog_bucket: Annotated[
        AssociationOne[AssuranceExpectationCatalogStubEntity],
        NoInverse(),
    ] = Rel(description="Parent catalog capsule")  # type: ignore[assignment]

    depth_axis: Annotated[
        AssociationOne[AssuranceSpecificationDepthAxisEntity],
        NoInverse(),
    ] = Rel(description="Depth posture on catalog spine")  # type: ignore[assignment]


AssuranceExpectationOutlineNodeEntity.model_rebuild()
