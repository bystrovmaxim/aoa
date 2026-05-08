# src/maxitor/samples/store/entities/store_mesh_order_invoice_bridge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(
    description="Parallel billing bridge between orders and invoicing artefacts (creates cyclic routing options in ERD)",
    domain=StoreDomain,
)
class StoreOrderInvoiceBridgeEntity(BaseEntity):
    id: str = Field(description="Bridge id")
    lifecycle: SalesOrderLifecycle = Field(description="Bridge lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Upstream order artefact")  # type: ignore[assignment]

    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Downstream invoicing artefact")  # type: ignore[assignment]


StoreOrderInvoiceBridgeEntity.model_rebuild()
