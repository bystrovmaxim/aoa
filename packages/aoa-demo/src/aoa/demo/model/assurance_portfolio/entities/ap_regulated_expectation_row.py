# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_regulated_expectation_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseDetailEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_expectation_catalog_stub import (
    AssuranceExpectationCatalogStubCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceExpectationGenreAxisCoreEntity,
    AssuranceExpectationPhaseAxisCoreEntity,
)


@entity(description="Versioned expectation corpus entry (requirement analogue)", domain=AssurancePortfolioDomain)
class AssuranceRegulatedExpectationRowDetailEntity(BaseDetailEntity):
    id: str = Field(description="Expectation entry id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Expectation row lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    catalog_bucket: Annotated[
        AssociationOne[AssuranceExpectationCatalogStubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Containing catalog"
    )

    genre_axis: Annotated[
        AssociationOne[AssuranceExpectationGenreAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Expectation genre discriminator"
    )

    phase_axis: Annotated[
        AssociationOne[AssuranceExpectationPhaseAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Expectation lifecycle phase"
    )


AssuranceRegulatedExpectationRowDetailEntity.model_rebuild()
