# src/maxitor/samples/analytics/entities/analytics_er_cycle_quad_stub.py
"""
Four analytics sketch entities wired as directed 4-cycle A\u2192B\u2192C\u2192D\u2192A.

Exercises **minimum closure length four** with dual reciprocal ``AssociationOne`` fields per node.
One-way links from vertices A/B into telemetry and sampling stubs merge the quad with analytics spine entities.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, Inverse, Lifecycle, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.analytics_canonical_telemetry_row import AnalyticsCanonicalTelemetryRowEntity


class _AnDirectedCycleSketchLifecycle(Lifecycle):
    _template = Lifecycle().state("open", "Open").to("settled").initial().state("settled", "Settled").final()


@entity(description="Analytics quad vertex A (\u2192B / \u2190D reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadAEntity(BaseEntity):
    id: str = Field(description="Vertex A id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    follow_b: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadBEntity],
        Inverse(AnalyticsDirectedCycleQuadBEntity, "back_from_a"),
    ] = Rel(description="Perimeter A\u2192B")  # type: ignore[assignment]

    back_from_d: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadDEntity],
        Inverse(AnalyticsDirectedCycleQuadDEntity, "follow_a"),
    ] = Rel(description="Closing hop D\u2192A pair")  # type: ignore[assignment]


@entity(description="Analytics quad vertex B (\u2190A / \u2192C reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadBEntity(BaseEntity):
    id: str = Field(description="Vertex B id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_a: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadAEntity],
        Inverse(AnalyticsDirectedCycleQuadAEntity, "follow_b"),
    ] = Rel(description="Reciprocal B\u2192A")  # type: ignore[assignment]

    follow_c: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadCEntity],
        Inverse(AnalyticsDirectedCycleQuadCEntity, "back_from_b"),
    ] = Rel(description="Perimeter B\u2192C")  # type: ignore[assignment]

    anchor_canonical_telemetry_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Connects quad vertex B to canonical telemetry facet chain")  # type: ignore[assignment]


@entity(description="Analytics quad vertex C (\u2190B / \u2192D reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadCEntity(BaseEntity):
    id: str = Field(description="Vertex C id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_b: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadBEntity],
        Inverse(AnalyticsDirectedCycleQuadBEntity, "follow_c"),
    ] = Rel(description="Reciprocal C\u2192B")  # type: ignore[assignment]

    follow_d: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadDEntity],
        Inverse(AnalyticsDirectedCycleQuadDEntity, "back_from_c"),
    ] = Rel(description="Perimeter C\u2192D")  # type: ignore[assignment]


@entity(description="Analytics quad vertex D (\u2190C / \u2192A reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadDEntity(BaseEntity):
    id: str = Field(description="Vertex D id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_c: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadCEntity],
        Inverse(AnalyticsDirectedCycleQuadCEntity, "follow_d"),
    ] = Rel(description="Reciprocal D\u2192C")  # type: ignore[assignment]

    follow_a: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadAEntity],
        Inverse(AnalyticsDirectedCycleQuadAEntity, "back_from_d"),
    ] = Rel(description="Perimeter D\u2192A")  # type: ignore[assignment]


AnalyticsDirectedCycleQuadAEntity.model_rebuild()
AnalyticsDirectedCycleQuadBEntity.model_rebuild()
AnalyticsDirectedCycleQuadCEntity.model_rebuild()
AnalyticsDirectedCycleQuadDEntity.model_rebuild()
