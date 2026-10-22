# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_ripple_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sweep_instruction import BillingSweepInstructionCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Settlement ripple memo on sweep branch", domain=BillingDomain)
class SettlementRippleCorrectionCoreEntity(BaseCoreEntity):
    id: str = Field(description="Memo id")
    lifecycle: BillingDenseLifecycle = Field(description="Ripple correction lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    sweep: Annotated[
        AssociationOne[BillingSweepInstructionCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Parent sweep instruction"
    )  # type: ignore[assignment]

    ripple_sequence: int = Field(description="Monotonic ripple attempt within sweep", ge=0)
    ripple_amount_minor: int = Field(description="Memoized adjustment in minor units")
    settlement_lane: str = Field(description="Ledger lane code")
    trace_token: str = Field(description="End-to-end reconciliation token")


SettlementRippleCorrectionCoreEntity.model_rebuild()
