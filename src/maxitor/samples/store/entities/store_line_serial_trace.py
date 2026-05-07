# src/maxitor/samples/store/entities/store_line_serial_trace.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Serialized lot linkage on line", domain=StoreDomain)
class LineSerialLotTraceEntity(BaseEntity):
    id: str = Field(description="LineSerialLotTraceEntity id")
    lifecycle: SalesOrderLineLifecycle = Field(description="LineSerialLotTraceEntity lifecycle")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line anchor")  # type: ignore[assignment]


LineSerialLotTraceEntity.model_rebuild()
