# src/maxitor/samples/billing/entities/funding_window_hint.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sweep_instruction import BillingSweepInstructionEntity


@entity(description="Funding window anchored on sweep instruction", domain=BillingDomain)
class FundingWindowHintEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Liquidity facet lifecycle")
    id: str = Field(description="Window id")

    sweep: Annotated[
        AssociationOne[BillingSweepInstructionEntity],
        NoInverse(),
    ] = Rel(description="Parent sweep instruction surface")  # type: ignore[assignment]


FundingWindowHintEntity.model_rebuild()
