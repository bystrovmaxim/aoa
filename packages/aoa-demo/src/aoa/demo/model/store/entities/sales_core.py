# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_core.py
"""
Store sales core triangle — mutual ``Inverse`` on three ``BaseEntity`` classes.

``CustomerAccountCoreEntity``, ``SalesOrderCoreEntity``, and ``SalesOrderLineDetailEntity`` share this module because
:class:`~aoa.action_machine.domain.relation_markers.Inverse` captures partner types at class-body time,
and importing them from separate modules would circular-import before all three classes exist. Thin
re-export modules (:file:`customer_account.py`, :file:`order_record.py`, :file:`line_item.py`) keep
stable import paths without duplicating declarations.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDetailEntity,
    CompositeMany,
    Inverse,
    NoInverse,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.entities.payment_event_log import PaymentEventLogCoreEntity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity
from aoa.demo.model.identity.entities.identity_person_hub import IdentityPersonHubCoreEntity
from aoa.demo.model.store.entities.customer_account_lifecycle import CustomerAccountLifecycle
from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.demo.model.store.entities.sales_order_line_lifecycle import SalesOrderLineLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Registered customer", domain=StoreDomain)
class CustomerAccountCoreEntity(BaseCoreEntity):
    id: str = Field(description="Customer id")
    lifecycle: CustomerAccountLifecycle = Field(description="Account lifecycle")
    name: str = Field(description="Display name")
    email: str = Field(description="Email")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    identity_party: Annotated[
        AssociationOne[IdentityPersonHubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Canonical person aggregate in the identity bounded context"
    )

    orders: Annotated[
        AssociationMany[SalesOrderCoreEntity],
        Inverse(SalesOrderCoreEntity, "customer"),
    ] = Field(
        description="Orders"
    )


@entity(description="Customer order", domain=StoreDomain)
class SalesOrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    amount: float = Field(description="Total", ge=0)
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    lifecycle: SalesOrderLifecycle = Field(description="Lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    customer: Annotated[
        AssociationOne[CustomerAccountCoreEntity],
        Inverse(CustomerAccountCoreEntity, "orders"),
    ] = Field(
        description="Customer"
    )

    order_lines: Annotated[
        CompositeMany[SalesOrderLineDetailEntity],
        Inverse(SalesOrderLineDetailEntity, "order"),
    ] = Field(
        description="Line items"
    )

    payment_capture_audit: Annotated[
        AssociationOne[PaymentEventLogCoreEntity],
        NoInverse(),
    ] = Field(
        description="Settlement-side payment telemetry for this storefront order"
    )


@entity(description="Order line", domain=StoreDomain)
class SalesOrderLineDetailEntity(BaseDetailEntity):
    id: str = Field(description="Item id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Line lifecycle")
    product_name: str = Field(description="Product")
    quantity: int = Field(description="Qty", ge=1)
    unit_price: float = Field(description="Unit price", ge=0)

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    catalog_product: Annotated[
        AssociationOne[CatalogProductCoreEntity],
        NoInverse(),
    ] = Field(
        description="Anchored SKU row from the commerce catalog"
    )

    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        Inverse(SalesOrderCoreEntity, "order_lines"),
    ] = Field(
        description="Parent order"
    )


CustomerAccountCoreEntity.model_rebuild()
SalesOrderCoreEntity.model_rebuild()
SalesOrderLineDetailEntity.model_rebuild()
