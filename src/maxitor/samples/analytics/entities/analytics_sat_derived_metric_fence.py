# src/maxitor/samples/analytics/entities/analytics_sat_derived_metric_fence.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_sat_dimension_slice_stub import DimensionSliceStubEntity


@entity(description="Derived metric concurrency fence stacking on dimension slice ingress branch", domain=AnalyticsDomain)
class DerivedMetricFenceEntity(BaseEntity):
    lifecycle: AnalyticsFactLifecycle = Field(description="DerivedMetricFenceEntity lifecycle")
    id: str = Field(description="Fence id")

    slice_stub: Annotated[
        AssociationOne[DimensionSliceStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream dimension slice facet")  # type: ignore[assignment]


DerivedMetricFenceEntity.model_rebuild()
