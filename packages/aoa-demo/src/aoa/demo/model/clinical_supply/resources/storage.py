# packages/aoa-demo/src/aoa/demo/model/clinical_supply/resources/storage.py
"""ClinicalSupplyStorage — the store that holds the clinical supply domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.clinical_supply.domain import ClinicalSupplyDomain
from aoa.demo.model.data_sources.clinical_supply_data_source import ClinicalSupplyDataSource


@meta(description="Stores the clinical supply model (stub)", domain=ClinicalSupplyDomain)
class ClinicalSupplyStorage(BaseStorage[ClinicalSupplyDataSource]):
    """Hold the clinical supply domain's entities; the demo never opens it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
