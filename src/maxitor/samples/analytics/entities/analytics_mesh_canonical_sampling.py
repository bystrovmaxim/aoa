# src/maxitor/samples/analytics/entities/analytics_mesh_canonical_sampling.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_canonical_telemetry_row import AnalyticsCanonicalTelemetryRowEntity
from maxitor.samples.analytics.entities.analytics_sampling_policy import AnalyticsSamplingPolicyEntity


@entity(description="Short-circuit between canonical telemetry egress and exploratory sampling subgraph", domain=AnalyticsDomain)
class AnalyticsCanonicalSamplingCorrelateEntity(BaseEntity):
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Correlator lifecycle")
    id: str = Field(description="Correlator id")

    canonical_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Canonical telemetry anchor")  # type: ignore[assignment]

    sampling_policy: Annotated[
        AssociationOne[AnalyticsSamplingPolicyEntity],
        NoInverse(),
    ] = Rel(description="Sampling workload anchor")  # type: ignore[assignment]


AnalyticsCanonicalSamplingCorrelateEntity.model_rebuild()
