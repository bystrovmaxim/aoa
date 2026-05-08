# packages/aoa-maxitor/src/aoa/maxitor/samples/analytics/entities/analytics_aggregate_sketch_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.analytics.domain import AnalyticsDomain
from aoa.maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from aoa.maxitor.samples.analytics.entities.analytics_sampling_policy import AnalyticsSamplingPolicyEntity


@entity(description="Sketch aggregate stub following sampling policy (two-node branch)", domain=AnalyticsDomain)
class AnalyticsAggregateSketchStubEntity(BaseEntity):
    id: str = Field(description="Sketch id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Sketch stub lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    policy: Annotated[
        AssociationOne[AnalyticsSamplingPolicyEntity],
        NoInverse(),
    ] = Rel(description="Parent sampling policy")  # type: ignore[assignment]


AnalyticsAggregateSketchStubEntity.model_rebuild()
