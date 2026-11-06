# packages/aoa-demo/src/aoa/demo/model/data_sources/telemetry_pipeline_data_source.py
"""TelemetryPipelineDataSource — the telemetry pipeline store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The telemetry pipeline store, kept in memory")
class TelemetryPipelineDataSource(InMemoryDataSource):
    """A demo store kept in the process: the telemetry pipeline domain's rows."""
