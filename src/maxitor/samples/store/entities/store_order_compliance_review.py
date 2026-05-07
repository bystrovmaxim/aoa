# src/maxitor/samples/store/entities/store_order_compliance_review.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Manual compliance review stub", domain=StoreDomain)
class ComplianceReviewQueueEntity(BaseEntity):
    id: str = Field(description="ComplianceReviewQueueEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="ComplianceReviewQueueEntity lifecycle")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


ComplianceReviewQueueEntity.model_rebuild()
