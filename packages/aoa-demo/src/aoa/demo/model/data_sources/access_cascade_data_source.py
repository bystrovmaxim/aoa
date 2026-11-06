# packages/aoa-demo/src/aoa/demo/model/data_sources/access_cascade_data_source.py
"""AccessCascadeDataSource — the access cascade store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The access cascade store, kept in memory")
class AccessCascadeDataSource(InMemoryDataSource):
    """A demo store kept in the process: the access cascade domain's rows."""
