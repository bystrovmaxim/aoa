# src/maxitor/samples/analytics/entities/analytics_canonical_telemetry_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_dedup_bloom_row import AnalyticsDedupBloomRowEntity


@entity(description="Canonical telemetry facet on dedup spine (no shared fact hub)", domain=AnalyticsDomain)
class AnalyticsCanonicalTelemetryRowEntity(BaseEntity):
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Canonical telemetry lifecycle")
    id: str = Field(description="Row id")

    dedup: Annotated[
        AssociationOne[AnalyticsDedupBloomRowEntity],
        NoInverse(),
    ] = Rel(description="Dedup bloom parent")  # type: ignore[assignment]


AnalyticsCanonicalTelemetryRowEntity.model_rebuild()
