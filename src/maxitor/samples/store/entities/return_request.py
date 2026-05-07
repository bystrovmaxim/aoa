# src/maxitor/samples/store/entities/return_request.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Return request row", domain=StoreDomain)
class ReturnRequestEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Return lifecycle")
    id: str = Field(description="Return request id")
    reason: str = Field(description="Return reason")
    status: str = Field(description="Return status")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Returned order")  # type: ignore[assignment]


ReturnRequestEntity.model_rebuild()
