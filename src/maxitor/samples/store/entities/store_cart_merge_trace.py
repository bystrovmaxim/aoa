# src/maxitor/samples/store/entities/store_cart_merge_trace.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import CustomerAccountEntity


@entity(description="Cart merge diagnostics hanging off buyer profile graph", domain=StoreDomain)
class CartMergeTraceEntity(BaseEntity):
    id: str = Field(description="Trace id")
    lifecycle: SalesOrderLifecycle = Field(description="Merge trace lifecycle")

    customer: Annotated[
        AssociationOne[CustomerAccountEntity],
        NoInverse(),
    ] = Rel(description="Parent customer aggregate")  # type: ignore[assignment]


CartMergeTraceEntity.model_rebuild()
