# src/maxitor/samples/store/entities/store_order_gift_wrap.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Gift wrap add-on", domain=StoreDomain)
class GiftWrapAddonEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="GiftWrapAddonEntity lifecycle")
    id: str = Field(description="GiftWrapAddonEntity id")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


GiftWrapAddonEntity.model_rebuild()
