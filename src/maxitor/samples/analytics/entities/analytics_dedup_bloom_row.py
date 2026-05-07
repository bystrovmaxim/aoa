# src/maxitor/samples/analytics/entities/analytics_dedup_bloom_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_ingress_batch import AnalyticsIngressBatchEntity


@entity(description="Dedup bloom facet on ingress batch", domain=AnalyticsDomain)
class AnalyticsDedupBloomRowEntity(BaseEntity):
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Dedup lifecycle")
    id: str = Field(description="Bloom row id")

    batch: Annotated[
        AssociationOne[AnalyticsIngressBatchEntity],
        NoInverse(),
    ] = Rel(description="Inbound batch linkage")  # type: ignore[assignment]


AnalyticsDedupBloomRowEntity.model_rebuild()
