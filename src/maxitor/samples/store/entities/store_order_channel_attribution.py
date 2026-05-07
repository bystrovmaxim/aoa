# src/maxitor/samples/store/entities/store_order_channel_attribution.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Order channel attribution facet", domain=StoreDomain)
class OrderChannelAttributionEntity(BaseEntity):
    id: str = Field(description="OrderChannelAttributionEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="OrderChannelAttributionEntity lifecycle")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


OrderChannelAttributionEntity.model_rebuild()
