# src/maxitor/samples/billing/entities/billing_sat_fee_schedule_ptr.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_interchange_slice import InterchangeAssessmentSliceEntity


@entity(description="Fee schedule facet following interchange slice spine", domain=BillingDomain)
class MerchantFeeSchedulePointerEntity(BaseEntity):
    id: str = Field(description="Pointer id")
    lifecycle: BillingDenseLifecycle = Field(description="Fee schedule lifecycle")

    interchange_slice: Annotated[
        AssociationOne[InterchangeAssessmentSliceEntity],
        NoInverse(),
    ] = Rel(description="Parent interchange economics row")  # type: ignore[assignment]

    mcc_bucket_code: str = Field(description="Merchant category bucket key")
    interchange_program_name: str = Field(description="Issuer-branded program moniker")
    fee_effective_from_iso: str = Field(description="Schedule effective timestamp (UTC)")
    rate_card_version: str = Field(description="Published rate card revision id")


MerchantFeeSchedulePointerEntity.model_rebuild()
