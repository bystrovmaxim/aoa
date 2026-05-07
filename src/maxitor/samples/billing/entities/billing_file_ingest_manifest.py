# src/maxitor/samples/billing/entities/billing_file_ingest_manifest.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingPipelineLifecycle


@entity(description="Billing file ingest manifest", domain=BillingDomain)
class BillingFileIngestManifestEntity(BaseEntity):
    lifecycle: BillingPipelineLifecycle = Field(description="Ingest lifecycle")
    id: str = Field(description="Manifest id")


BillingFileIngestManifestEntity.model_rebuild()
