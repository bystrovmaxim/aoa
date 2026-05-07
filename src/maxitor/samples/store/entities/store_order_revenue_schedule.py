# src/maxitor/samples/store/entities/store_order_revenue_schedule.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Deferred revenue cadence stub", domain=StoreDomain)
class RevenueDeferralScheduleEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="RevenueDeferralScheduleEntity lifecycle")
    id: str = Field(description="RevenueDeferralScheduleEntity id")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


RevenueDeferralScheduleEntity.model_rebuild()
