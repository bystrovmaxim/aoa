# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/discount_application.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Discount application row", domain=StoreDomain)
class DiscountApplicationEntity(BaseEntity):
    id: str = Field(description="Discount application id")
    lifecycle: SalesOrderLifecycle = Field(description="Discount lifecycle")
    coupon_code: str = Field(description="Coupon code")
    discount_amount: float = Field(description="Discount amount", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Discounted order")  # type: ignore[assignment]

    acquisition_attribution_head: Annotated[
        AssociationOne[AcquisitionChannelLedgerEntity],
        NoInverse(),
    ] = Rel(description="Catalog acquisition ledger head for attributed demand")  # type: ignore[assignment]

DiscountApplicationEntity.model_rebuild()
