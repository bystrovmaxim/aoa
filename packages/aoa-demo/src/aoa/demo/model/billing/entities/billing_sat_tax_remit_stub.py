# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_tax_remit_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sat_cash_apply_hint import CashApplicationHintCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Tax remittance advice continuing cash-application liquidity chain", domain=BillingDomain)
class TaxRemittanceAdviceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Advice stub id")
    lifecycle: BillingDenseLifecycle = Field(description="Remittance lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    cash_apply_hint: Annotated[
        AssociationOne[CashApplicationHintCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Upstream cash-application hint"
    )  # type: ignore[assignment]

    jurisdiction_code: str = Field(description="Tax authority region code")
    filing_period_id: str = Field(description="Closed reporting period key")
    accrued_minor_units: int = Field(description="Accrued obligation in minor currency units", ge=0)
    remittance_deadline_iso: str = Field(description="Mandatory remittance timestamp (UTC)")


TaxRemittanceAdviceCoreEntity.model_rebuild()
