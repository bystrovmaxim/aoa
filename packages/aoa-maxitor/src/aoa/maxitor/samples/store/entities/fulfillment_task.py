# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/fulfillment_task.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.inventory.entities.inv_lot_snapshot_ledger import LotSnapshotLedgerEntity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Fulfillment task row", domain=StoreDomain)
class FulfillmentTaskEntity(BaseEntity):
    id: str = Field(description="Task id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Fulfillment task lifecycle")
    assignee: str = Field(description="Assigned worker")
    task_kind: str = Field(description="Task kind")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Target order line")  # type: ignore[assignment]

    lot_inventory_slice: Annotated[
        AssociationOne[LotSnapshotLedgerEntity],
        NoInverse(),
    ] = Rel(description="Inventory lot snapshot consulted for allocation")  # type: ignore[assignment]

FulfillmentTaskEntity.model_rebuild()
