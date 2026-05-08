# src/maxitor/samples/assurance_portfolio/entities/ap_actor_duty_coupling.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorEntity
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_reference_axes import AssuranceDutyTemplateAxisEntity


@entity(description="Join between actor and duty catalogue (user_has_role analogue)", domain=AssurancePortfolioDomain)
class AssuranceActorDutyCouplingEntity(BaseEntity):
    id: str = Field(description="Coupling id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Coupling lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    actor: Annotated[
        AssociationOne[AssuranceFacilityActorEntity],
        NoInverse(),
    ] = Rel(description="Subject actor")  # type: ignore[assignment]

    duty_axis: Annotated[
        AssociationOne[AssuranceDutyTemplateAxisEntity],
        NoInverse(),
    ] = Rel(description="Assigned duty template")  # type: ignore[assignment]


AssuranceActorDutyCouplingEntity.model_rebuild()
