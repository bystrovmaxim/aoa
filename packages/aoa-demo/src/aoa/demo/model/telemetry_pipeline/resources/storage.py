# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/resources/storage.py
"""TelemetryPipelineStorage — the store that holds the telemetry pipeline domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.telemetry_pipeline.entities.routed_observation_slice_entity import (
    RoutedObservationSliceDetailEntity,
)
from aoa.demo.model.telemetry_pipeline.entities.telemetry_ingest_envelope_entity import (
    TelemetryIngestEnvelopeCoreEntity,
)


@meta(description="Stores the telemetry pipeline model (stub)")
@entities(
    RoutedObservationSliceDetailEntity,
    TelemetryIngestEnvelopeCoreEntity,
)
class TelemetryPipelineStorage(BaseStorage):
    """Hold the telemetry pipeline domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
