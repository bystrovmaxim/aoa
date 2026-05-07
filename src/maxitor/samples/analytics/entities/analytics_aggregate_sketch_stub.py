# src/maxitor/samples/analytics/entities/analytics_aggregate_sketch_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_sampling_policy import AnalyticsSamplingPolicyEntity


@entity(description="Sketch aggregate stub following sampling policy (two-node branch)", domain=AnalyticsDomain)
class AnalyticsAggregateSketchStubEntity(BaseEntity):
    id: str = Field(description="Sketch id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Sketch stub lifecycle")

    policy: Annotated[
        AssociationOne[AnalyticsSamplingPolicyEntity],
        NoInverse(),
    ] = Rel(description="Parent sampling policy")  # type: ignore[assignment]


AnalyticsAggregateSketchStubEntity.model_rebuild()
