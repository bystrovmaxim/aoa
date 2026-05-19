# packages/aoa-examples/src/aoa/examples/model/analytics/entities/analytics_sat_dimension_slice_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.analytics.domain import AnalyticsDomain
from aoa.examples.model.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from aoa.examples.model.analytics.entities.analytics_ingress_batch import AnalyticsIngressBatchEntity


@entity(description="Dimension slice branching off ingress batches (parallel to dedup spine)", domain=AnalyticsDomain)
class DimensionSliceStubEntity(BaseEntity):
    id: str = Field(description="Slice id")
    lifecycle: AnalyticsFactLifecycle = Field(description="DimensionSliceStubEntity lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    ingress_batch: Annotated[
        AssociationOne[AnalyticsIngressBatchEntity],
        NoInverse(),
    ] = Rel(description="Owning ingest workload batch")  # type: ignore[assignment]


DimensionSliceStubEntity.model_rebuild()
