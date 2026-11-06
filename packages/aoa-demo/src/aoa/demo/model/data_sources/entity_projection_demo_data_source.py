# packages/aoa-demo/src/aoa/demo/model/data_sources/entity_projection_demo_data_source.py
"""EntityProjectionDemoDataSource — the entity projection demo store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The entity projection demo store, kept in memory")
class EntityProjectionDemoDataSource(InMemoryDataSource):
    """A demo store kept in the process: the entity projection demo's rows."""
