# src/maxitor/samples/store/entities/payment_authorization.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


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
    ] = Rel(description="Authorized order")  # type: ignore[assignment]


PaymentAuthorizationEntity.model_rebuild()
