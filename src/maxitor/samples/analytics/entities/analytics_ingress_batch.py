# src/maxitor/samples/analytics/entities/analytics_ingress_batch.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle


@entity(description="Ingress batch spine head", domain=AnalyticsDomain)
class AnalyticsIngressBatchEntity(BaseEntity):
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Batch lifecycle")
    id: str = Field(description="Batch id")


AnalyticsIngressBatchEntity.model_rebuild()
