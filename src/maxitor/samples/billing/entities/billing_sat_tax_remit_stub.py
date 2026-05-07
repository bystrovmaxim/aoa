# src/maxitor/samples/billing/entities/billing_sat_tax_remit_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_cash_apply_hint import CashApplicationHintEntity


@entity(description="Tax remittance advice continuing cash-application liquidity chain", domain=BillingDomain)
class TaxRemittanceAdviceEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Remittance lifecycle")
    id: str = Field(description="Advice stub id")

    cash_apply_hint: Annotated[
        AssociationOne[CashApplicationHintEntity],
        NoInverse(),
    ] = Rel(description="Upstream cash-application hint")  # type: ignore[assignment]


TaxRemittanceAdviceEntity.model_rebuild()
