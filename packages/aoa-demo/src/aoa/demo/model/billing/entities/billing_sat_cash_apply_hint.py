# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_cash_apply_hint.py
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.funding_window_hint import FundingWindowHintCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity

if TYPE_CHECKING:
    from aoa.demo.model.billing.entities.arbitration_brief_stub import ArbitrationBriefStubCoreEntity


@entity(description="Cash application routing hint chained from liquidity funding window facet", domain=BillingDomain)
class CashApplicationHintCoreEntity(BaseCoreEntity):
    id: str = Field(description="Hint id")
    lifecycle: BillingDenseLifecycle = Field(description="Cash hint lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    funding_window: Annotated[
        AssociationOne[FundingWindowHintCoreEntity],
        NoInverse(),
    ] = Field(
        description="Upstream funding guidance row"
    )

    arbitration_brief: Annotated[
        AssociationOne[ArbitrationBriefStubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Arbitration brief context for disputed cash-application routing"
    )

    routing_lane: str = Field(description="Cash-application routing lane key")
    tentative_clearing_date_iso: str = Field(description="Target clearing calendar date")
    residual_tolerance_minor: int = Field(description="Allowed residuals in minor units", ge=0)
    priority_bucket: str = Field(description="Ops escalation bucket")
