# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_sat_ripple_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.billing_sweep_instruction import BillingSweepInstructionEntity


@entity(description="Settlement ripple memo on sweep branch", domain=BillingDomain)
class SettlementRippleCorrectionEntity(BaseEntity):
    id: str = Field(description="Memo id")
    lifecycle: BillingDenseLifecycle = Field(description="Ripple correction lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    sweep: Annotated[
        AssociationOne[BillingSweepInstructionEntity],
        NoInverse(),
    ] = Rel(description="Parent sweep instruction")  # type: ignore[assignment]

    ripple_sequence: int = Field(description="Monotonic ripple attempt within sweep", ge=0)
    ripple_amount_minor: int = Field(description="Memoized adjustment in minor units")
    settlement_lane: str = Field(description="Ledger lane code")
    trace_token: str = Field(description="End-to-end reconciliation token")


SettlementRippleCorrectionEntity.model_rebuild()
