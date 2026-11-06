# packages/aoa-demo/src/aoa/demo/model/data_sources/assurance_portfolio_data_source.py
"""AssurancePortfolioDataSource — the assurance portfolio store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The assurance portfolio store, kept in memory")
class AssurancePortfolioDataSource(InMemoryDataSource):
    """A demo store kept in the process: the assurance portfolio domain's rows."""
