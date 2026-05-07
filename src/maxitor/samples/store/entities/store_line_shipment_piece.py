# src/maxitor/samples/store/entities/store_line_shipment_piece.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity, SalesOrderLineEntity


@entity(description="Shipment piece bridging line + header (dense mesh cue)", domain=StoreDomain)
class LineShipmentPieceEntity(BaseEntity):
    lifecycle: SalesOrderLineLifecycle = Field(description="Shipment piece lifecycle")
    id: str = Field(description="Piece id")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Line anchor")  # type: ignore[assignment]

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent order duplicate anchor")  # type: ignore[assignment]


LineShipmentPieceEntity.model_rebuild()
