# packages/aoa-demo/src/aoa/demo/model/catalog_custody/resources/storage.py
"""CatalogCustodyStorage — the store that holds the catalog custody domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.catalog_custody.entities.custody_audit_event_entity import CustodyAuditEventCoreEntity
from aoa.demo.model.catalog_custody.entities.regulated_stock_keeping_unit_row_entity import (
    RegulatedStockKeepingUnitRowDetailEntity,
)


@meta(description="Stores the catalog custody model (stub)")
@entities(
    CustodyAuditEventCoreEntity,
    RegulatedStockKeepingUnitRowDetailEntity,
)
class CatalogCustodyStorage(BaseStorage):
    """Hold the catalog custody domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
