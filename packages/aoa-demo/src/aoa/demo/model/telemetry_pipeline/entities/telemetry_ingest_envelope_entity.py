# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/entities/telemetry_ingest_envelope_entity.py
"""Immutable envelope captured at edge ingest boundaries."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@entity(description="Edge ingest envelope keyed by opaque batch locator", domain=TelemetryPipelineDomain)
class TelemetryIngestEnvelopeEntity(BaseEntity):
    envelope_id: str = Field(description="Envelope surrogate key")
    edge_site_code: str = Field(description="Colo / CDN PoP mnemonic")
    raw_payload_checksum: str = Field(description="Integrity token for replicated payload")
