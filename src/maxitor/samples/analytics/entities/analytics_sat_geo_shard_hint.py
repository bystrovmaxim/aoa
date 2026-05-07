# src/maxitor/samples/analytics/entities/analytics_sat_geo_shard_hint.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_sat_replay_watermark_stub import ReplayWatermarkStubEntity


@entity(description="Geo shard hint chaining off replay watermark bridge", domain=AnalyticsDomain)
class GeoShardHintEntity(BaseEntity):
    lifecycle: AnalyticsFactLifecycle = Field(description="Geo shard hint lifecycle")
    id: str = Field(description="Shard hint id")

    replay_watermark: Annotated[
        AssociationOne[ReplayWatermarkStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream replay watermark row")  # type: ignore[assignment]


GeoShardHintEntity.model_rebuild()
