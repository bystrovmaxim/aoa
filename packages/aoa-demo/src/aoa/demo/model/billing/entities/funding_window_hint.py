# packages/aoa-demo/src/aoa/demo/model/billing/entities/funding_window_hint.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sweep_instruction import BillingSweepInstructionCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Funding window anchored on sweep instruction", domain=BillingDomain)
class FundingWindowHintCoreEntity(BaseCoreEntity):
    id: str = Field(description="Window id")
    lifecycle: BillingDenseLifecycle = Field(description="Liquidity facet lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    sweep: Annotated[
        AssociationOne[BillingSweepInstructionCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parent sweep instruction surface"
    )

    window_label: str = Field(description="Human-visible liquidity lane label")
    opens_at_iso: str = Field(description="Window opens (UTC ISO-8601)")
    closes_at_iso: str = Field(description="Window closes (UTC ISO-8601)")
    liquidity_band: str = Field(description="Tier label for cash availability")


FundingWindowHintCoreEntity.model_rebuild()
