# src/maxitor/samples/analytics/entities/analytics_metric_rollup_staging.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_canonical_telemetry_row import (
    AnalyticsCanonicalTelemetryRowEntity,
)


@entity(description="Metric rollup staging chained from canonical row", domain=AnalyticsDomain)
class AnalyticsMetricRollupStagingEntity(BaseEntity):
    id: str = Field(description="Staging shard id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Rollup lifecycle")

    canonical_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Canonical telemetry parent")  # type: ignore[assignment]


AnalyticsMetricRollupStagingEntity.model_rebuild()
