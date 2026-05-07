# src/maxitor/samples/store/entities/store_order_packing_slip.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(description="Packing slip facet tied directly to fulfilment parcels (supply spine)", domain=StoreDomain)
class PackingSlipEntity(BaseEntity):
    id: str = Field(description="Slip id")
    lifecycle: SalesOrderLifecycle = Field(description="Packing slip lifecycle")

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Parent shipment parcel artefact")  # type: ignore[assignment]


PackingSlipEntity.model_rebuild()
