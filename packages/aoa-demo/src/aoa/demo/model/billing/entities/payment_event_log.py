# packages/aoa-demo/src/aoa/demo/model/billing/entities/payment_event_log.py
"""Minimal entity so the ``billing`` bounded context appears on the entity graph."""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.payment_lifecycle import PaymentEventLifecycle
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Append-only payment event (sample)", domain=BillingDomain)
class PaymentEventLogCoreEntity(BaseCoreEntity):
    id: str = Field(description="Event id")
    lifecycle: PaymentEventLifecycle = Field(description="Payment event lifecycle")
    kind: str = Field(description="Event kind label")
    amount_minor_units: int = Field(description="Settlement amount in minor currency units", ge=0)
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="ISO-4217 currency code")
    processor_reference: str = Field(description="Upstream processor correlation id")
    occurred_at_utc: str = Field(description="Event timestamp (UTC ISO-8601)")
    settlement_batch_id: str = Field(description="Batch id when event was rolled into settlement")


PaymentEventLogCoreEntity.model_rebuild()
