# src/maxitor/samples/assurance_portfolio/entities/ap_execution_attempt_ticket.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Concrete execution instantiation (test run analogue)", domain=AssurancePortfolioDomain)
class AssuranceExecutionAttemptTicketEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Execution lifecycle")
    id: str = Field(description="Execution attempt id")


AssuranceExecutionAttemptTicketEntity.model_rebuild()
