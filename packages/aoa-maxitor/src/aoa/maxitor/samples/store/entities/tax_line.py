# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/tax_line.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Tax line row", domain=StoreDomain)
class TaxLineEntity(BaseEntity):
    id: str = Field(description="Tax line id")
    lifecycle: SalesOrderLifecycle = Field(description="Tax line lifecycle")
    tax_code: str = Field(description="Tax code")
    tax_amount: float = Field(description="Tax amount", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Taxed order")  # type: ignore[assignment]


TaxLineEntity.model_rebuild()
