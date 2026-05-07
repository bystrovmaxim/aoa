# src/maxitor/samples/billing/entities/billing_sat_cash_apply_hint.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.funding_window_hint import FundingWindowHintEntity


@entity(description="Cash application routing hint chained from liquidity funding window facet", domain=BillingDomain)
class CashApplicationHintEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Cash hint lifecycle")
    id: str = Field(description="Hint id")

    funding_window: Annotated[
        AssociationOne[FundingWindowHintEntity],
        NoInverse(),
    ] = Rel(description="Upstream funding guidance row")  # type: ignore[assignment]


CashApplicationHintEntity.model_rebuild()
