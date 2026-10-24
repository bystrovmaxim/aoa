# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_payout_plan.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Payout plan rollup", domain=BillingDomain)
class BillingPayoutPlanCoreEntity(BaseCoreEntity):
    id: str = Field(description="Plan id")
    lifecycle: BillingDenseLifecycle = Field(description="Payout lifecycle")
    plan_vendor_code: str = Field(description="Internal plan mnemonic")
    settlement_currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Payout denomination currency")
    planned_minor_units_total: int = Field(description="Planned disbursement ceiling in minor units", ge=0)
    horizon_calendar_days: int = Field(description="Rolling coverage window", ge=1, le=3650)
    payout_frequency_hint: str = Field(description="Expected cadence label (weekly, intra-day)")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")


BillingPayoutPlanCoreEntity.model_rebuild()
