# src/maxitor/samples/store/entities/store_mesh_order_parcel_handoff.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(
    description="Junction aligning header orders with parcel fulfilment subgraph (dense mesh cue)",
    domain=StoreDomain,
)
class StoreOrderParcelHandoffEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Handoff lifecycle")
    id: str = Field(description="Link id")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Referenced order aggregate")  # type: ignore[assignment]

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Referenced shipment parcel artefact")  # type: ignore[assignment]


StoreOrderParcelHandoffEntity.model_rebuild()
