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

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Upstream order artefact")  # type: ignore[assignment]

    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Downstream invoicing artefact")  # type: ignore[assignment]


StoreOrderInvoiceBridgeEntity.model_rebuild()
