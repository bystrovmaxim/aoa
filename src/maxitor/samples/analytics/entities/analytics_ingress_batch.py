# src/maxitor/samples/analytics/entities/analytics_ingress_batch.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle


@entity(description="Ingress batch spine head", domain=AnalyticsDomain)
class AnalyticsIngressBatchEntity(BaseEntity):
    id: str = Field(description="Batch id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Batch lifecycle")

    billing_manifest_correlation: Annotated[
        AssociationOne["BillingFileIngestManifestEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Billing ingest manifest keyed for analytic batch lineage")  # type: ignore[assignment]


from maxitor.samples.billing.entities.billing_file_ingest_manifest import (  # noqa: E402
    BillingFileIngestManifestEntity,
)

AnalyticsIngressBatchEntity.model_rebuild()
