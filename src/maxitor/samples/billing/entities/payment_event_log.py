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
    amount_minor_units: int = Field(description="Settlement amount in minor currency units", ge=0)
    currency_iso: str = Field(description="ISO-4217 currency code", min_length=3, max_length=3)
    processor_reference: str = Field(description="Upstream processor correlation id")
    occurred_at_utc: str = Field(description="Event timestamp (UTC ISO-8601)")
    settlement_batch_id: str = Field(description="Batch id when event was rolled into settlement")


PaymentEventLogEntity.model_rebuild()
