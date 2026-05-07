# src/maxitor/samples/analytics/entities/analytics_sat_time_bucket_mapper.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_aggregate_sketch_stub import AnalyticsAggregateSketchStubEntity


@entity(description="Time bucket mapper on sketch sampling pipeline continuation", domain=AnalyticsDomain)
class TimeBucketMapperEntity(BaseEntity):
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Mapper lifecycle")
    id: str = Field(description="Mapper id")

    sketch_stub: Annotated[
        AssociationOne[AnalyticsAggregateSketchStubEntity],
        NoInverse(),
    ] = Rel(description="Parent aggregate sketch")  # type: ignore[assignment]


TimeBucketMapperEntity.model_rebuild()
