# src/maxitor/samples/store/entities/store_line_kit_explosion.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Kit explosion child line trace", domain=StoreDomain)
class KitExplosionLineEntity(BaseEntity):
    lifecycle: SalesOrderLineLifecycle = Field(description="KitExplosionLineEntity lifecycle")
    id: str = Field(description="KitExplosionLineEntity id")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line anchor")  # type: ignore[assignment]


KitExplosionLineEntity.model_rebuild()
