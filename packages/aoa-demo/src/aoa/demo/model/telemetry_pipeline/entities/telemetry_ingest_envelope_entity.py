# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/entities/telemetry_ingest_envelope_entity.py
"""Immutable envelope captured at edge ingest boundaries."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.inventory.entities.inv_facility_warehouse import FacilityWarehouseCoreEntity
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@entity(description="Edge ingest envelope keyed by opaque batch locator", domain=TelemetryPipelineDomain)
class TelemetryIngestEnvelopeCoreEntity(BaseCoreEntity):
    envelope_id: str = Field(description="Envelope surrogate key")
    edge_site_code: str = Field(description="Colo / CDN PoP mnemonic")
    raw_payload_checksum: str = Field(description="Integrity token for replicated payload")
    source_warehouse: Annotated[
        AssociationOne[FacilityWarehouseCoreEntity],
        NoInverse(),
    ] = Field(description="The warehouse whose edge site sent the envelope")
