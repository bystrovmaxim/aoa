# packages/aoa-demo/src/aoa/demo/model/data_sources/analytics_data_source.py
"""AnalyticsDataSource — the analytics store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The analytics store, kept in memory")
class AnalyticsDataSource(InMemoryDataSource):
    """A demo store kept in the process: the analytics domain's rows."""
