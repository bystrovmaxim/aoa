# src/maxitor/samples/billing/entities/billing_payout_plan.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Payout plan rollup", domain=BillingDomain)
class BillingPayoutPlanEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Payout lifecycle")
    id: str = Field(description="Plan id")
    plan_vendor_code: str = Field(description="Internal plan mnemonic")
    settlement_currency_iso: str = Field(description="Payout denomination currency")
    planned_minor_units_total: int = Field(description="Planned disbursement ceiling in minor units", ge=0)
    horizon_calendar_days: int = Field(description="Rolling coverage window", ge=1, le=3650)
    payout_frequency_hint: str = Field(description="Expected cadence label (weekly, intra-day)")


BillingPayoutPlanEntity.model_rebuild()
