# packages/aoa-demo/src/aoa/demo/model/data_sources/generalization_shapes_data_source.py
"""GeneralizationShapesDataSource — the generalization shapes store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The generalization shapes store, kept in memory")
class GeneralizationShapesDataSource(InMemoryDataSource):
    """A demo store kept in the process: the generalization shapes domain's rows."""
