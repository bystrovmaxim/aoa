# src/maxitor/samples/assurance_portfolio/entities/ap_regulated_expectation_row.py
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
    AssuranceExpectationGenreAxisEntity,
    AssuranceExpectationPhaseAxisEntity,
)


@entity(description="Versioned expectation corpus entry (requirement analogue)", domain=AssurancePortfolioDomain)
class AssuranceRegulatedExpectationRowEntity(BaseEntity):
    id: str = Field(description="Expectation entry id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Expectation row lifecycle")

    catalog_bucket: Annotated[
        AssociationOne[AssuranceExpectationCatalogStubEntity],
        NoInverse(),
    ] = Rel(description="Containing catalog")  # type: ignore[assignment]

    genre_axis: Annotated[
        AssociationOne[AssuranceExpectationGenreAxisEntity],
        NoInverse(),
    ] = Rel(description="Expectation genre discriminator")  # type: ignore[assignment]

    phase_axis: Annotated[
        AssociationOne[AssuranceExpectationPhaseAxisEntity],
        NoInverse(),
    ] = Rel(description="Expectation lifecycle phase")  # type: ignore[assignment]


AssuranceRegulatedExpectationRowEntity.model_rebuild()
