# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_execution_attempt_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.identity.entities.identity_person_hub import IdentityPersonHubCoreEntity


@entity(description="Concrete execution instantiation (test run analogue)", domain=AssurancePortfolioDomain)
class AssuranceExecutionAttemptTicketCoreEntity(BaseCoreEntity):
    id: str = Field(description="Execution attempt id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Execution lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    actor_person_hub: Annotated[
        AssociationOne[IdentityPersonHubCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Identity hub for executor attribution and segregation boundaries"
    )  # type: ignore[assignment]


AssuranceExecutionAttemptTicketCoreEntity.model_rebuild()
