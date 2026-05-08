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
    id: str = Field(description="Offset id")
    lifecycle: BillingDenseLifecycle = Field(description="Mirror offset lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    fee_schedule_pointer: Annotated[
        AssociationOne[MerchantFeeSchedulePointerEntity],
        NoInverse(),
    ] = Rel(description="Upstream fee schedule pointer")  # type: ignore[assignment]

    mirror_partition_id: str = Field(description="Sharding partition for mirrored ledger")
    observation_lag_seconds: int = Field(description="Replication lag observed at capture", ge=0)
    imbalance_minor_units: int = Field(description="Detected mirror drift in minor currency units")


LedgerMirrorOffsetEntity.model_rebuild()
