# src/maxitor/samples/billing/entities/chargeback_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.payment_event_log import PaymentEventLogEntity


@entity(description="Chargeback case opened on payment-event", domain=BillingDomain)
class ChargebackTicketEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Dispute lifecycle")
    id: str = Field(description="Ticket id")

    payment_event: Annotated[
        AssociationOne[PaymentEventLogEntity],
        NoInverse(),
    ] = Rel(description="Funding payment event anchor")  # type: ignore[assignment]


ChargebackTicketEntity.model_rebuild()
