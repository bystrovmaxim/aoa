# packages/aoa-examples/src/aoa/examples/model/store/ocel_trace_builder.py
"""
Store OCEL trace builders — ``StoreDomain`` entities and ``OcelFrame`` rows.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Shared construction of storefront entities and ``OcelFrame`` payloads for OCEL
export actions. Keeps domain field names aligned with ``sales_core`` entities.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain import AssociationOne, BaseEntity
from aoa.action_machine.plugin.ocel import OcelFrame
from aoa.action_machine.plugin.ocel.dto import OcelAttribute
from aoa.examples.model.catalog.entities.catalog_product_lifecycle import CatalogProductLifecycle
from aoa.examples.model.catalog.entities.product_row import CatalogProductEntity
from aoa.examples.model.inventory.entities.inv_dense_lifecycle import InvPipelineLifecycle
from aoa.examples.model.inventory.entities.inv_facility_warehouse import FacilityWarehouseEntity
from aoa.examples.model.store.entities.customer_account import CustomerAccountEntity
from aoa.examples.model.store.entities.customer_account_lifecycle import CustomerAccountLifecycle
from aoa.examples.model.store.entities.fulfillment_task import FulfillmentTaskEntity
from aoa.examples.model.store.entities.line_item import SalesOrderLineEntity
from aoa.examples.model.store.entities.order_record import SalesOrderEntity
from aoa.examples.model.store.entities.payment_capture import PaymentCaptureEntity
from aoa.examples.model.store.entities.return_request import ReturnRequestEntity
from aoa.examples.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.examples.model.store.entities.sales_order_line_lifecycle import SalesOrderLineLifecycle
from aoa.examples.model.store.entities.shipment_parcel import ShipmentParcelEntity


def build_customer_account(
    *,
    customer_id: str,
    name: str,
    email: str,
    storefront_channel: str = "ecommerce",
) -> CustomerAccountEntity:
    """Materialize a storefront customer with active lifecycle."""
    return CustomerAccountEntity(
        id=customer_id,
        lifecycle=CustomerAccountLifecycle("active"),
        name=name,
        email=email,
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
    )


def build_sales_order(
    *,
    order_id: str,
    customer: CustomerAccountEntity,
    amount: float,
    lifecycle_state: str,
    storefront_channel: str = "ecommerce",
) -> SalesOrderEntity:
    """Materialize an order with loaded ``customer`` for one-hop E2O export."""
    return SalesOrderEntity(
        id=order_id,
        amount=amount,
        currency="USD",
        lifecycle=SalesOrderLifecycle(lifecycle_state),
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
        customer=AssociationOne(id=customer.id, entity=customer),
    )


def build_catalog_product(*, product_id: str, sku: str, title: str, unit_price: float) -> CatalogProductEntity:
    """Materialize a catalog SKU referenced from an order line."""
    return CatalogProductEntity(
        id=product_id,
        lifecycle=CatalogProductLifecycle("active"),
        sku=sku,
        title=title,
        list_price=unit_price,
        commercial_region_code="US",
        channel_partner_tag="direct",
        compliance_locale="en-US",
    )


def build_order_line(
    *,
    line_id: str,
    order: SalesOrderEntity,
    product: CatalogProductEntity,
    quantity: int,
    unit_price: float,
    lifecycle_state: str,
    storefront_channel: str,
) -> SalesOrderLineEntity:
    """Materialize a line with loaded ``order`` and ``catalog_product`` peers."""
    return SalesOrderLineEntity(
        id=line_id,
        lifecycle=SalesOrderLineLifecycle(lifecycle_state),
        product_name=product.title,
        quantity=quantity,
        unit_price=unit_price,
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        catalog_product=AssociationOne(id=product.id, entity=product),
        order=AssociationOne(id=order.id, entity=order),
    )


def build_payment_capture(
    *,
    capture_id: str,
    order: SalesOrderEntity,
    amount: float,
    storefront_channel: str,
) -> PaymentCaptureEntity:
    """Materialize a capture row with loaded ``order``."""
    return PaymentCaptureEntity(
        id=capture_id,
        lifecycle=SalesOrderLifecycle("confirmed"),
        amount=amount,
        captured_at="2026-05-19T12:00:00Z",
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
        order=AssociationOne(id=order.id, entity=order),
    )


def build_fulfillment_task(
    *,
    task_id: str,
    order_line: SalesOrderLineEntity,
    assignee: str,
    storefront_channel: str,
) -> FulfillmentTaskEntity:
    """Materialize a pick task with loaded ``order_line``."""
    return FulfillmentTaskEntity(
        id=task_id,
        lifecycle=SalesOrderLineLifecycle("fulfilled"),
        assignee=assignee,
        task_kind="pick",
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
        order_line=AssociationOne(id=order_line.id, entity=order_line),
    )


def build_facility_warehouse(*, facility_id: str) -> FacilityWarehouseEntity:
    """Materialize a warehouse facility for shipment events."""
    return FacilityWarehouseEntity(
        id=facility_id,
        lifecycle=InvPipelineLifecycle("anchored"),
        facility_tz="America/Los_Angeles",
        capacity_cu_m=12000.0,
        hazmat_classification="none",
        cycle_count_due_unix=1_800_000_000,
        dock_door_anchor="D-07",
        velocity_bucket="A",
    )


def build_shipment_parcel(
    *,
    parcel_id: str,
    order: SalesOrderEntity,
    facility: FacilityWarehouseEntity,
    storefront_channel: str,
) -> ShipmentParcelEntity:
    """Materialize a parcel with loaded ``order`` and ``origin_facility``."""
    return ShipmentParcelEntity(
        id=parcel_id,
        lifecycle=SalesOrderLifecycle("shipped"),
        carrier="UPS",
        tracking_number=f"1Z{parcel_id.replace('-', '').upper()}",
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
        order=AssociationOne(id=order.id, entity=order),
        origin_facility=AssociationOne(id=facility.id, entity=facility),
    )


def build_return_request(
    *,
    return_id: str,
    order: SalesOrderEntity,
    reason: str,
    storefront_channel: str,
) -> ReturnRequestEntity:
    """Materialize a return row with loaded ``order``."""
    return ReturnRequestEntity(
        id=return_id,
        lifecycle=SalesOrderLifecycle("shipped"),
        reason=reason,
        status="opened",
        storefront_channel=storefront_channel,
        compliance_rating="low",
        fulfillment_priority=1,
        tax_jurisdiction_stub="US-CA",
        order=AssociationOne(id=order.id, entity=order),
    )


def build_order_ocel_frame(
    order: SalesOrderEntity,
    *,
    qualifier: str,
    event_attributes: list[OcelAttribute],
) -> OcelFrame[SalesOrderEntity]:
    """Wrap a loaded order graph as one ``OcelFrame`` participation row."""
    return OcelFrame(
        object=order,
        qualifier=qualifier,
        attributes=event_attributes,
    )


def build_entity_ocel_frame(
    entity: BaseEntity,
    *,
    qualifier: str,
    event_attributes: list[OcelAttribute],
) -> OcelFrame[Any]:
    """Generic ``OcelFrame`` wrapper for any export root entity."""
    return OcelFrame(
        object=entity,
        qualifier=qualifier,
        attributes=event_attributes,
    )
