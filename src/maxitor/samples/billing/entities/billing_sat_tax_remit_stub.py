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
    id: str = Field(description="Advice stub id")
    lifecycle: BillingDenseLifecycle = Field(description="Remittance lifecycle")

    cash_apply_hint: Annotated[
        AssociationOne[CashApplicationHintEntity],
        NoInverse(),
    ] = Rel(description="Upstream cash-application hint")  # type: ignore[assignment]

    jurisdiction_code: str = Field(description="Tax authority region code")
    filing_period_id: str = Field(description="Closed reporting period key")
    accrued_minor_units: int = Field(description="Accrued obligation in minor currency units", ge=0)
    remittance_deadline_iso: str = Field(description="Mandatory remittance timestamp (UTC)")


TaxRemittanceAdviceEntity.model_rebuild()
