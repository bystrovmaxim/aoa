# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/resources/storage.py
"""TelemetryPipelineStorage — the store that holds the telemetry pipeline domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Stores the telemetry pipeline model (stub)", domain=TelemetryPipelineDomain)
class TelemetryPipelineStorage(BaseStorage):
    """Hold the telemetry pipeline domain's entities; the demo never opens it."""
