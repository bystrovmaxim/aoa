# packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_invoice_line_tie.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.invoice_record import InvoiceRecordCoreEntity
from aoa.demo.model.store.entities.sales_core import SalesOrderLineDetailEntity
from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Structured tie reconciling invoicing artefacts with fulfilment-line rows", domain=StoreDomain)
class StoreInvoiceLineTieCoreEntity(BaseCoreEntity):
    id: str = Field(description="Correlation id")
    lifecycle: SalesOrderLifecycle = Field(description="Tie lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    invoice: Annotated[
        AssociationOne[InvoiceRecordCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Owning invoice artefact"
    )  # type: ignore[assignment]

    order_line: Annotated[
        AssociationOne[SalesOrderLineDetailEntity],
        NoInverse(),
    ] = Rel(
        description="Owning order line artefact"
    )  # type: ignore[assignment]


StoreInvoiceLineTieCoreEntity.model_rebuild()
