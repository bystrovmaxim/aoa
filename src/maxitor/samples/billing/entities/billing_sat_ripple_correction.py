# src/maxitor/samples/billing/entities/billing_sat_ripple_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sweep_instruction import BillingSweepInstructionEntity


@entity(description="Settlement ripple memo on sweep branch (distinct from ingest / interchange spines)", domain=BillingDomain)
class SettlementRippleCorrectionEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Ripple correction lifecycle")
    id: str = Field(description="Memo id")

    sweep: Annotated[
        AssociationOne[BillingSweepInstructionEntity],
        NoInverse(),
    ] = Rel(description="Parent sweep instruction")  # type: ignore[assignment]


SettlementRippleCorrectionEntity.model_rebuild()
