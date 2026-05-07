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
    file_logical_name: str = Field(description="Declared file label before landing")
    content_sha256_hex: str = Field(description="Hex digest after virus scan checkpoint")
    approximate_row_count: int = Field(description="Parser-estimated ingest rows", ge=0)
    batch_correlation_key: str = Field(description="Cross-feed dedupe grouping key")
    originating_feed_system: str = Field(description="Source system moniker (issuer, PSP, ERP)")


BillingFileIngestManifestEntity.model_rebuild()
