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
    id: str = Field(description="Hint id")
    lifecycle: BillingDenseLifecycle = Field(description="Cash hint lifecycle")

    funding_window: Annotated[
        AssociationOne[FundingWindowHintEntity],
        NoInverse(),
    ] = Rel(description="Upstream funding guidance row")  # type: ignore[assignment]

    arbitration_brief: Annotated[
        AssociationOne["ArbitrationBriefStubEntity"],  # noqa: F821, UP037
        NoInverse(),
    ] = Rel(description="Arbitration brief context for disputed cash-application routing")  # type: ignore[assignment]

    routing_lane: str = Field(description="Cash-application routing lane key")
    tentative_clearing_date_iso: str = Field(description="Target clearing calendar date")
    residual_tolerance_minor: int = Field(description="Allowed residuals in minor units", ge=0)
    priority_bucket: str = Field(description="Ops escalation bucket")
