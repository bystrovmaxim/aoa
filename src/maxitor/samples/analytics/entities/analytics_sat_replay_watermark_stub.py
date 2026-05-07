# src/maxitor/samples/analytics/entities/analytics_sat_replay_watermark_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_metric_rollup_staging import AnalyticsMetricRollupStagingEntity


@entity(description="Replay watermark on rollup staging egress (orthogonal to DQ branch)", domain=AnalyticsDomain)
class ReplayWatermarkStubEntity(BaseEntity):
    id: str = Field(description="Watermark id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Watermark lifecycle")

    rollup_staging: Annotated[
        AssociationOne[AnalyticsMetricRollupStagingEntity],
        NoInverse(),
    ] = Rel(description="Owning rollup staging row")  # type: ignore[assignment]


ReplayWatermarkStubEntity.model_rebuild()
