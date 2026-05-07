# src/maxitor/samples/store/entities/refund_request.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Refund request row", domain=StoreDomain)
class RefundRequestEntity(BaseEntity):
    id: str = Field(description="Refund id")
    lifecycle: SalesOrderLifecycle = Field(description="Refund lifecycle")
    amount: float = Field(description="Requested refund amount", ge=0)
    reason: str = Field(description="Refund reason")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Refunded order")  # type: ignore[assignment]


RefundRequestEntity.model_rebuild()
