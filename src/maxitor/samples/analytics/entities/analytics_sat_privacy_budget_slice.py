# src/maxitor/samples/analytics/entities/analytics_sat_privacy_budget_slice.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle


@entity(description="Privacy budget ledger slice isolated as its own subgraph root", domain=AnalyticsDomain)
class PrivacyBudgetSliceEntity(BaseEntity):
    id: str = Field(description="Slice id")
    lifecycle: AnalyticsFactLifecycle = Field(description="Privacy slice lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")


PrivacyBudgetSliceEntity.model_rebuild()
