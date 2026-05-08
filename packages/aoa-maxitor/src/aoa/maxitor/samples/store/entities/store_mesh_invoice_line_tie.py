# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/store_mesh_invoice_line_tie.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Structured tie reconciling invoicing artefacts with fulfilment-line rows", domain=StoreDomain)
class StoreInvoiceLineTieEntity(BaseEntity):
    id: str = Field(description="Correlation id")
    lifecycle: SalesOrderLifecycle = Field(description="Tie lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Owning invoice artefact")  # type: ignore[assignment]

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line artefact")  # type: ignore[assignment]


StoreInvoiceLineTieEntity.model_rebuild()
