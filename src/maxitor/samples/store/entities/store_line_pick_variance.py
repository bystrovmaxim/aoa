# src/maxitor/samples/store/entities/store_line_pick_variance.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Pick-pack variance ledger", domain=StoreDomain)
class PickVarianceRecordEntity(BaseEntity):
    id: str = Field(description="PickVarianceRecordEntity id")
    lifecycle: SalesOrderLineLifecycle = Field(description="PickVarianceRecordEntity lifecycle")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line anchor")  # type: ignore[assignment]


PickVarianceRecordEntity.model_rebuild()
