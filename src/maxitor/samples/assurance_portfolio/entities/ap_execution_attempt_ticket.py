# src/maxitor/samples/assurance_portfolio/entities/ap_execution_attempt_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Concrete execution instantiation (test run analogue)", domain=AssurancePortfolioDomain)
class AssuranceExecutionAttemptTicketEntity(BaseEntity):
    id: str = Field(description="Execution attempt id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Execution lifecycle")

    actor_person_hub: Annotated[
        AssociationOne["IdentityPersonHubEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Identity hub for executor attribution and segregation boundaries")  # type: ignore[assignment]


from maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity  # noqa: E402

AssuranceExecutionAttemptTicketEntity.model_rebuild()
