# src/maxitor/samples/billing/entities/billing_payout_plan.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Payout plan rollup (liquidity subtree head)", domain=BillingDomain)
class BillingPayoutPlanEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Payout lifecycle")
    id: str = Field(description="Plan id")


BillingPayoutPlanEntity.model_rebuild()
