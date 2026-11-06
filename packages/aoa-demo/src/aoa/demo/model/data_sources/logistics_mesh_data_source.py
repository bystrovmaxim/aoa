# packages/aoa-demo/src/aoa/demo/model/data_sources/logistics_mesh_data_source.py
"""LogisticsMeshDataSource — the logistics mesh store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The logistics mesh store, kept in memory")
class LogisticsMeshDataSource(InMemoryDataSource):
    """A demo store kept in the process: the logistics mesh domain's rows."""
