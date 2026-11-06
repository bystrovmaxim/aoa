# packages/aoa-demo/src/aoa/demo/model/data_sources/settlement_desks_data_source.py
"""SettlementDesksDataSource — the settlement desks store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The settlement desks store, kept in memory")
class SettlementDesksDataSource(InMemoryDataSource):
    """A demo store kept in the process: the settlement desks domain's rows."""
