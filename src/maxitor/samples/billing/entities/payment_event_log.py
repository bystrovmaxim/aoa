# src/maxitor/samples/billing/entities/payment_event_log.py
"""Минимальная сущность, чтобы bounded context ``billing`` появился в графе сущностей."""

from pydantic import Field

from action_machine.domain import BaseEntity, entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.payment_lifecycle import PaymentEventLifecycle


@entity(description="Append-only payment event (sample)", domain=BillingDomain)
class PaymentEventLogEntity(BaseEntity):
    lifecycle: PaymentEventLifecycle = Field(description="Payment event lifecycle")
    id: str = Field(description="Event id")
    kind: str = Field(description="Event kind label")
