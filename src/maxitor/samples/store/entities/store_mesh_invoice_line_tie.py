# src/maxitor/samples/store/entities/store_mesh_invoice_line_tie.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Structured tie reconciling invoicing artefacts with fulfilment-line rows", domain=StoreDomain)
class StoreInvoiceLineTieEntity(BaseEntity):
    id: str = Field(description="Correlation id")
    lifecycle: SalesOrderLifecycle = Field(description="Tie lifecycle")

    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Owning invoice artefact")  # type: ignore[assignment]

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line artefact")  # type: ignore[assignment]


StoreInvoiceLineTieEntity.model_rebuild()
