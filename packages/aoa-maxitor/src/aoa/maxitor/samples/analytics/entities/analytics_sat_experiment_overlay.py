# packages/aoa-maxitor/src/aoa/maxitor/samples/analytics/entities/analytics_sat_experiment_overlay.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.analytics.domain import AnalyticsDomain
from aoa.maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from aoa.maxitor.samples.analytics.entities.analytics_canonical_telemetry_row import (
    AnalyticsCanonicalTelemetryRowEntity,
)


@entity(description="Experiment overlay anchored on canonical telemetry spine (distinct from ingest branch)", domain=AnalyticsDomain)
class ExperimentOverlayEntity(BaseEntity):
    id: str = Field(description="Overlay id")
    lifecycle: AnalyticsFactLifecycle = Field(description="Experiment overlay lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    canonical_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Canonical telemetry lineage parent")  # type: ignore[assignment]


ExperimentOverlayEntity.model_rebuild()
