# src/maxitor/samples/store/entities/store_order_geo_fence.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Geo compliance fence row", domain=StoreDomain)
class OrderGeoFenceEntity(BaseEntity):
    id: str = Field(description="OrderGeoFenceEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="OrderGeoFenceEntity lifecycle")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


OrderGeoFenceEntity.model_rebuild()
