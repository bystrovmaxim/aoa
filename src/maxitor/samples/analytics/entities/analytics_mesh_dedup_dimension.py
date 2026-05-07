# src/maxitor/samples/analytics/entities/analytics_mesh_dedup_dimension.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_dedup_bloom_row import AnalyticsDedupBloomRowEntity
from maxitor.samples.analytics.entities.analytics_sat_dimension_slice_stub import DimensionSliceStubEntity


@entity(description="Tie row connecting dedupe spine ingress with parallel dimension branching", domain=AnalyticsDomain)
class AnalyticsDedupDimensionCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlator id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Correlator lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    dedup_row: Annotated[
        AssociationOne[AnalyticsDedupBloomRowEntity],
        NoInverse(),
    ] = Rel(description="Dedup bloom anchor")  # type: ignore[assignment]

    dimension_stub: Annotated[
        AssociationOne[DimensionSliceStubEntity],
        NoInverse(),
    ] = Rel(description="Dimension slice anchor")  # type: ignore[assignment]


AnalyticsDedupDimensionCorrelateEntity.model_rebuild()
