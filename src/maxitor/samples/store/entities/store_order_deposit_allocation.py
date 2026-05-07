# src/maxitor/samples/store/entities/store_order_deposit_allocation.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle


@entity(description="Deposit allocation keyed to invoice artefacts instead of repeating order spine only", domain=StoreDomain)
class DepositAllocationEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Deposit allocation lifecycle")
    id: str = Field(description="Allocation id")

    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Target invoice artefact")  # type: ignore[assignment]


DepositAllocationEntity.model_rebuild()
