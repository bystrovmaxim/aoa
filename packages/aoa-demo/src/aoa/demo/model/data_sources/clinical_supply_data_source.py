# packages/aoa-demo/src/aoa/demo/model/data_sources/clinical_supply_data_source.py
"""ClinicalSupplyDataSource — the clinical supply store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The clinical supply store, kept in memory")
class ClinicalSupplyDataSource(InMemoryDataSource):
    """A demo store kept in the process: the clinical supply domain's rows."""
