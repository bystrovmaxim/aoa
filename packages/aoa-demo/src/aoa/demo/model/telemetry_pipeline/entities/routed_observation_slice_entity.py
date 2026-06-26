# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/entities/routed_observation_slice_entity.py
"""Post-normalisation slice emitted into correlation ladders."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.telemetry_pipeline.entities.telemetry_ingest_envelope_entity import (
    TelemetryIngestEnvelopeEntity,
)
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@entity(description="Deterministic routed span slice tied back to ingest envelope", domain=TelemetryPipelineDomain)
class RoutedObservationSliceEntity(BaseEntity):
    slice_id: str = Field(description="Routing slice surrogate key")
    severity_bucket_stub: str = Field(description="P1 | P2 | synthetic demo bucket")
    source_envelope: Annotated[
        AssociationOne[TelemetryIngestEnvelopeEntity],
        NoInverse(),
    ] = Rel(
        description="Source envelope powering this routed slice"
    )  # type: ignore[assignment]
