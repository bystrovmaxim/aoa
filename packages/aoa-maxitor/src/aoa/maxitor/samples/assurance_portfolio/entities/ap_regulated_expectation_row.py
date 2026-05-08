# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_regulated_expectation_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.maxitor.samples.assurance_portfolio.entities.ap_expectation_catalog_stub import (
    AssuranceExpectationCatalogStubEntity,
)
from aoa.maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.maxitor.samples.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceExpectationGenreAxisEntity,
    AssuranceExpectationPhaseAxisEntity,
)


@entity(description="Versioned expectation corpus entry (requirement analogue)", domain=AssurancePortfolioDomain)
class AssuranceRegulatedExpectationRowEntity(BaseEntity):
    id: str = Field(description="Expectation entry id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Expectation row lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
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
