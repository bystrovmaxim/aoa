# packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_er_cycle_quad_stub.py
"""
Four analytics sketch entities wired as directed 4-cycle A\u2192B\u2192C\u2192D\u2192A.

Exercises **minimum closure length four** with dual reciprocal ``AssociationOne`` fields per node.
One-way links from vertices A/B into telemetry and sampling stubs merge the quad with analytics spine entities.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseStateEntity,
    Inverse,
    Lifecycle,
    NoInverse,
    Rel,
    StateVocabulary,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.analytics.domain import AnalyticsDomain
from aoa.demo.model.analytics.entities.analytics_canonical_telemetry_row import (
    AnalyticsCanonicalTelemetryRowDetailEntity,
)


class _AnDirectedCycleSketchStateEntity(BaseStateEntity):
    """Status of the _AnDirectedCycleSketch axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class _AnDirectedCycleSketchLifecycle(Lifecycle, StateVocabulary):
    """Statuses and links of the _AnDirectedCycleSketchLifecycle axis."""

    OPEN = _AnDirectedCycleSketchStateEntity(code="open", display_name="Open", sort_order=1)
    SETTLED = _AnDirectedCycleSketchStateEntity(code="settled", display_name="Settled", sort_order=2)

    _template = Lifecycle().state(OPEN).to(SETTLED).initial().state(SETTLED).final()


@entity(description="Analytics quad vertex A (\u2192B / \u2190D reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadACoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex A id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    follow_b: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadBCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadBCoreEntity, "back_from_a"),
    ] = Rel(
        description="Perimeter A\u2192B"
    )  # type: ignore[assignment]

    back_from_d: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadDCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadDCoreEntity, "follow_a"),
    ] = Rel(
        description="Closing hop D\u2192A pair"
    )  # type: ignore[assignment]


@entity(description="Analytics quad vertex B (\u2190A / \u2192C reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadBCoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex B id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_a: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadACoreEntity],
        Inverse(AnalyticsDirectedCycleQuadACoreEntity, "follow_b"),
    ] = Rel(
        description="Reciprocal B\u2192A"
    )  # type: ignore[assignment]

    follow_c: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadCCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadCCoreEntity, "back_from_b"),
    ] = Rel(
        description="Perimeter B\u2192C"
    )  # type: ignore[assignment]

    anchor_canonical_telemetry_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowDetailEntity],
        NoInverse(),
    ] = Rel(
        description="Connects quad vertex B to canonical telemetry facet chain"
    )  # type: ignore[assignment]


@entity(description="Analytics quad vertex C (\u2190B / \u2192D reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadCCoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex C id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_b: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadBCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadBCoreEntity, "follow_c"),
    ] = Rel(
        description="Reciprocal C\u2192B"
    )  # type: ignore[assignment]

    follow_d: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadDCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadDCoreEntity, "back_from_c"),
    ] = Rel(
        description="Perimeter C\u2192D"
    )  # type: ignore[assignment]


@entity(description="Analytics quad vertex D (\u2190C / \u2192A reciprocal)", domain=AnalyticsDomain)
class AnalyticsDirectedCycleQuadDCoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex D id")
    lifecycle: _AnDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    ingress_batch_key: str = Field(description="Loader partition key echoed into lake prefixes")
    source_anchor_slug: str = Field(description="Upstream subsystem / connector anchor moniker")
    event_estimate: int = Field(description="Approximate attributable telemetry rows", ge=0)
    payload_byte_hint: int = Field(description="Compressed payload footprint hint bytes", ge=0)
    freshness_horizon_sec: int = Field(description="Skew allowance for unordered facts seconds", ge=0)
    privacy_tier_label: str = Field(description="Data-class label surfaced to rollup consumers")
    back_from_c: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadCCoreEntity],
        Inverse(AnalyticsDirectedCycleQuadCCoreEntity, "follow_d"),
    ] = Rel(
        description="Reciprocal D\u2192C"
    )  # type: ignore[assignment]

    follow_a: Annotated[
        AssociationOne[AnalyticsDirectedCycleQuadACoreEntity],
        Inverse(AnalyticsDirectedCycleQuadACoreEntity, "back_from_d"),
    ] = Rel(
        description="Perimeter D\u2192A"
    )  # type: ignore[assignment]


AnalyticsDirectedCycleQuadACoreEntity.model_rebuild()
AnalyticsDirectedCycleQuadBCoreEntity.model_rebuild()
AnalyticsDirectedCycleQuadCCoreEntity.model_rebuild()
AnalyticsDirectedCycleQuadDCoreEntity.model_rebuild()
