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
    lifecycle: BillingDenseLifecycle = Field(description="Fee schedule lifecycle")
    id: str = Field(description="Pointer id")

    interchange_slice: Annotated[
        AssociationOne[InterchangeAssessmentSliceEntity],
        NoInverse(),
    ] = Rel(description="Parent interchange economics row")  # type: ignore[assignment]


MerchantFeeSchedulePointerEntity.model_rebuild()
