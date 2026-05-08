# packages/aoa-maxitor/src/aoa/maxitor/samples/analytics/entities/analytics_sat_geo_shard_hint.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.analytics.domain import AnalyticsDomain
from aoa.maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from aoa.maxitor.samples.analytics.entities.analytics_sat_replay_watermark_stub import ReplayWatermarkStubEntity


@entity(description="Geo shard hint chaining off replay watermark bridge", domain=AnalyticsDomain)
class GeoShardHintEntity(BaseEntity):
    id: str = Field(description="Shard hint id")
    lifecycle: AnalyticsFactLifecycle = Field(description="Geo shard hint lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    replay_watermark: Annotated[
        AssociationOne[ReplayWatermarkStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream replay watermark row")  # type: ignore[assignment]


GeoShardHintEntity.model_rebuild()
