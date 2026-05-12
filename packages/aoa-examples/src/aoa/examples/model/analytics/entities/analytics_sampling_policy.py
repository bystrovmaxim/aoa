# packages/aoa-examples/src/aoa/examples/model/analytics/entities/analytics_sampling_policy.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.analytics.domain import AnalyticsDomain
from aoa.examples.model.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle


@entity(description="Parallel sampling subgraph head", domain=AnalyticsDomain)
class AnalyticsSamplingPolicyEntity(BaseEntity):
    id: str = Field(description="Policy id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Sampling lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")


AnalyticsSamplingPolicyEntity.model_rebuild()
