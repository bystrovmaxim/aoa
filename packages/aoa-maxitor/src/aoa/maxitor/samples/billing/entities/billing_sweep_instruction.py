# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_sweep_instruction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.billing_payout_plan import BillingPayoutPlanEntity


@entity(description="Sweep instruction under payout plan", domain=BillingDomain)
class BillingSweepInstructionEntity(BaseEntity):
    id: str = Field(description="Sweep id")
    lifecycle: BillingDenseLifecycle = Field(description="Sweep lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    payout_plan: Annotated[
        AssociationOne[BillingPayoutPlanEntity],
        NoInverse(),
    ] = Rel(description="Parent payout plan")  # type: ignore[assignment]

    corridor_code: str = Field(description="Treasury corridor identifier")
    priority_rank: int = Field(description="Relative ordering within plan", ge=0)
    netting_window_hours: int = Field(description="Aggregation window duration", ge=1, le=240)
    suspense_bucket_tag: str = Field(description="Default suspense bucket label")


BillingSweepInstructionEntity.model_rebuild()
