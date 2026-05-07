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

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    canonical_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Canonical telemetry parent")  # type: ignore[assignment]


AnalyticsMetricRollupStagingEntity.model_rebuild()
