# packages/aoa-examples/src/aoa/examples/model/store/entities/payment_authorization.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.store.entities.sales_core import SalesOrderEntity
from aoa.examples.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.examples.model.store.store_domain import StoreDomain


@entity(description="Payment authorization row", domain=StoreDomain)
class PaymentAuthorizationEntity(BaseEntity):
    id: str = Field(description="Authorization id")
    lifecycle: SalesOrderLifecycle = Field(description="Authorization lifecycle")
    provider: str = Field(description="PSP name")
    approved_amount: float = Field(description="Approved amount", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(
        description="Authorized order"
    )  # type: ignore[assignment]


PaymentAuthorizationEntity.model_rebuild()
