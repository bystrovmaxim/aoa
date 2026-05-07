# src/maxitor/samples/store/entities/fulfillment_task.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Fulfillment task row", domain=StoreDomain)
class FulfillmentTaskEntity(BaseEntity):
    lifecycle: SalesOrderLineLifecycle = Field(description="Fulfillment task lifecycle")
    id: str = Field(description="Task id")
    assignee: str = Field(description="Assigned worker")
    task_kind: str = Field(description="Task kind")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Target order line")  # type: ignore[assignment]


FulfillmentTaskEntity.model_rebuild()
