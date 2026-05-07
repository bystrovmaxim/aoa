# src/maxitor/samples/billing/entities/billing_sat_ledger_mirror_offset.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_fee_schedule_ptr import MerchantFeeSchedulePointerEntity


@entity(description="Ledger mirror continuation on interchange fee spine", domain=BillingDomain)
class LedgerMirrorOffsetEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Mirror offset lifecycle")
    id: str = Field(description="Offset id")

    fee_schedule_pointer: Annotated[
        AssociationOne[MerchantFeeSchedulePointerEntity],
        NoInverse(),
    ] = Rel(description="Upstream fee schedule pointer")  # type: ignore[assignment]


LedgerMirrorOffsetEntity.model_rebuild()
