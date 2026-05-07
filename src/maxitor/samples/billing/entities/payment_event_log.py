# src/maxitor/samples/billing/entities/payment_event_log.py
"""Minimal entity so the ``billing`` bounded context appears on the entity graph."""

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.payment_lifecycle import PaymentEventLifecycle


@entity(description="Append-only payment event (sample)", domain=BillingDomain)
class PaymentEventLogEntity(BaseEntity):
    lifecycle: PaymentEventLifecycle = Field(description="Payment event lifecycle")
    id: str = Field(description="Event id")
    kind: str = Field(description="Event kind label")


PaymentEventLogEntity.model_rebuild()
