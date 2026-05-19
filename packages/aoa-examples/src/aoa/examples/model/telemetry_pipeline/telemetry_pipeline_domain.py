# packages/aoa-examples/src/aoa/examples/model/telemetry_pipeline/telemetry_pipeline_domain.py
"""TelemetryPipelineDomain — cross-edge observability intake and enrichment."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class TelemetryPipelineDomain(BaseDomain):
    """Downlink ingestion, deterministic normalisation ladders, correlator overlays."""

    name = "telemetry_pipeline"
    description = "Edge → normalisation tiers → correlator overlays for incident responders"
