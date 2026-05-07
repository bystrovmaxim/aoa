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
    id: str = Field(description="Return request id")
    lifecycle: SalesOrderLifecycle = Field(description="Return lifecycle")
    reason: str = Field(description="Return reason")
    status: str = Field(description="Return status")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Returned order")  # type: ignore[assignment]

    reverse_logistics_metrics_batch: Annotated[
        AssociationOne["AnalyticsIngressBatchEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Analytics ingress shard for reverse-logistics telemetry")  # type: ignore[assignment]


from maxitor.samples.analytics.entities.analytics_ingress_batch import AnalyticsIngressBatchEntity  # noqa: E402

ReturnRequestEntity.model_rebuild()
