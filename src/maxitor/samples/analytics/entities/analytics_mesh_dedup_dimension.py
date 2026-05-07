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

    dedup_row: Annotated[
        AssociationOne[AnalyticsDedupBloomRowEntity],
        NoInverse(),
    ] = Rel(description="Dedup bloom anchor")  # type: ignore[assignment]

    dimension_stub: Annotated[
        AssociationOne[DimensionSliceStubEntity],
        NoInverse(),
    ] = Rel(description="Dimension slice anchor")  # type: ignore[assignment]


AnalyticsDedupDimensionCorrelateEntity.model_rebuild()
