# src/maxitor/samples/store/entities/store_order_split_bill.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Split billing allocation", domain=StoreDomain)
class SplitBillAllocationEntity(BaseEntity):
    id: str = Field(description="SplitBillAllocationEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="SplitBillAllocationEntity lifecycle")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


SplitBillAllocationEntity.model_rebuild()
