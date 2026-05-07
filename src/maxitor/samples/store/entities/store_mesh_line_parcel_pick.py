# src/maxitor/samples/store/entities/store_mesh_line_parcel_pick.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(description="Warehouse pick linkage between order lines and heterogeneous parcel batches", domain=StoreDomain)
class StoreLineParcelPickEntity(BaseEntity):
    id: str = Field(description="Pick id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Pick lifecycle")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Fulfilling order line artefact")  # type: ignore[assignment]

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Target parcel artefact")  # type: ignore[assignment]


StoreLineParcelPickEntity.model_rebuild()
