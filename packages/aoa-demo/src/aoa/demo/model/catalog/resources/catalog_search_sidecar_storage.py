# packages/aoa-demo/src/aoa/demo/model/catalog/resources/catalog_search_sidecar_storage.py
"""
CatalogSearchSidecarStorage — database-free demo storage with SQL lifecycle semantics.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent the domain's storage in the demo without opening a database connection.
The SQL lifecycle methods are harmless no-ops; inherited close remains safe.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Domain actions and entities -> CatalogSearchSidecarStorage -> SqlStorage contract
"""

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlStorage
from aoa.demo.model.catalog.entities.catalog_search_boost_weight import SearchBoostWeightCoreEntity


@meta(description="Search sidecar index (stub)")
@entities(
    SearchBoostWeightCoreEntity,
)
class CatalogSearchSidecarStorage(SqlStorage):
    """
    AI-CORE-BEGIN
    ROLE: Database-free storage for the demo domain.
    CONTRACT: Provide the SQL lifecycle without acquiring a connection.
    INVARIANTS: The class retains its Storage kind and domain metadata.
    AI-CORE-END
    """

    def __init__(self, rollup: bool = False) -> None:
        """Preserve the SQL contract’s rollup configuration."""
        super().__init__(rollup=rollup)

    async def open(self) -> None:
        """Keep the database-free store ready for use."""
        return None

    async def begin(self) -> None:
        """Accept a transaction boundary without external state."""
        return None

    async def commit(self) -> None:
        """Finish the demo transaction without persistence."""
        return None

    async def rollback(self) -> None:
        """Finish the demo transaction without external writes."""
        return None
