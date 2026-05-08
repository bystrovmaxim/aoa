# src/maxitor/samples/analytics/entities/analytics_sat_derived_metric_fence.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_sat_dimension_slice_stub import DimensionSliceStubEntity


@entity(description="Derived metric concurrency fence stacking on dimension slice ingress branch", domain=AnalyticsDomain)
class DerivedMetricFenceEntity(BaseEntity):
    id: str = Field(description="Fence id")
    lifecycle: AnalyticsFactLifecycle = Field(description="DerivedMetricFenceEntity lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    slice_stub: Annotated[
        AssociationOne[DimensionSliceStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream dimension slice facet")  # type: ignore[assignment]


DerivedMetricFenceEntity.model_rebuild()
