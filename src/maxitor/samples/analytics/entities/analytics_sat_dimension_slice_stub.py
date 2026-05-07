# src/maxitor/samples/analytics/entities/analytics_sat_dimension_slice_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_ingress_batch import AnalyticsIngressBatchEntity


@entity(description="Dimension slice branching off ingress batches (parallel to dedup spine)", domain=AnalyticsDomain)
class DimensionSliceStubEntity(BaseEntity):
    lifecycle: AnalyticsFactLifecycle = Field(description="DimensionSliceStubEntity lifecycle")
    id: str = Field(description="Slice id")

    ingress_batch: Annotated[
        AssociationOne[AnalyticsIngressBatchEntity],
        NoInverse(),
    ] = Rel(description="Owning ingest workload batch")  # type: ignore[assignment]


DimensionSliceStubEntity.model_rebuild()
