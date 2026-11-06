# packages/aoa-action-machine/src/aoa/action_machine/resources/in_memory/in_memory_data_source.py
"""
InMemoryDataSource — a store that lives in the process, shared by the resources that name it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every entity has a physical place: its resource names a data source. A store kept in
the process — a dictionary of rows, a cache, a test's fake database — is a data source
too. ``InMemoryDataSource`` is its kind: it holds one mapping, ``store``, that every
resource naming it reads and writes, and it lives from ``open()`` to ``close()``.

An application derives its own data source from this kind and creates it once; it
passes the instance to every resource that names it::

    @meta(description="Catalog kept in memory")
    class CatalogDataSource(InMemoryDataSource): ...

    @meta(description="Catalog", domain=CatalogDomain)
    class CatalogStorage(BaseStorage[CatalogDataSource]): ...

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- ``store`` is one mapping for the whole life of the data source; ``close()`` empties it.
- The data source holds no transaction: what a resource does with the rows is its own.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_data_source import BaseDataSource


@exclude_graph_model
class InMemoryDataSource(BaseDataSource):
    """
    AI-CORE-BEGIN
    ROLE: The kind of data source of a store that lives in the process.
    CONTRACT: ``store`` is one mapping shared by every resource that names the data source; ``open``/``close`` and ``async with``; ``close`` empties the store.
    INVARIANTS: Holds no transaction and no connection.
    AI-CORE-END
    """

    def __init__(self, store: dict[str, Any] | None = None) -> None:
        """
        Keep the mapping the resources share.

        Args:
            store: the rows to start from; a new empty mapping when ``None``.
        """
        self._store: dict[str, Any] = {} if store is None else store

    @property
    def store(self) -> dict[str, Any]:
        """The mapping every resource of this data source reads and writes."""
        return self._store

    async def open(self) -> None:
        """Nothing to open: the store is ready once the data source is built."""

    async def close(self) -> None:
        """Empty the store."""
        self._store.clear()

    async def __aenter__(self) -> InMemoryDataSource:
        """Open, and give the data source to the ``async with`` block."""
        await self.open()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close, whatever the block raised."""
        await self.close()
