# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_ledger_mirror_offset.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sat_fee_schedule_ptr import MerchantFeeSchedulePointerCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Ledger mirror continuation on interchange fee spine", domain=BillingDomain)
class LedgerMirrorOffsetCoreEntity(BaseCoreEntity):
    id: str = Field(description="Offset id")
    lifecycle: BillingDenseLifecycle = Field(description="Mirror offset lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    fee_schedule_pointer: Annotated[
        AssociationOne[MerchantFeeSchedulePointerCoreEntity],
        NoInverse(),
    ] = Field(
        description="Upstream fee schedule pointer"
    )

    mirror_partition_id: str = Field(description="Sharding partition for mirrored ledger")
    observation_lag_seconds: int = Field(description="Replication lag observed at capture", ge=0)
    imbalance_minor_units: int = Field(description="Detected mirror drift in minor currency units")


LedgerMirrorOffsetCoreEntity.model_rebuild()
