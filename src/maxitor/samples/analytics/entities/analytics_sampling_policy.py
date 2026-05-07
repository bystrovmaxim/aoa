# src/maxitor/samples/analytics/entities/analytics_sampling_policy.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle


@entity(description="Parallel sampling subgraph head", domain=AnalyticsDomain)
class AnalyticsSamplingPolicyEntity(BaseEntity):
    id: str = Field(description="Policy id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Sampling lifecycle")


AnalyticsSamplingPolicyEntity.model_rebuild()
