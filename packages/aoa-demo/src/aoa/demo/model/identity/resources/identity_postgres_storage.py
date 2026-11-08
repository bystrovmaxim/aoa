# packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_postgres_storage.py
"""
IdentityPostgresStorage — the identity domain over PostgreSQL, one connection per call.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This is the resource the demo route declares per call: ``IdentityPostgresStorage(pool=…)``
takes one connection from ``IdentityPool``, the identity database's pool, in
``open()`` and gives it back in ``close()``, so two concurrent calls never share a
session. The domain's
two operations come from ``IdentityStorage``; the storage primitive is the
connection the framework handed over.

Importing this module needs the ``postgres`` extra, because ``PostgresStorage``
imports the driver. That is why the demo reaches for it lazily — inside the
factory that builds the resource — and never at import time.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    IdentityPostgresStorage(IdentityStorage, PostgresStorage)
        │  open()/close()      -> pool.acquire / release          (once per call)
        │  read_person(id)     -> self._fetchrow(…)
        │  _list_persons(…)    -> self._fetch(…)               (ordered, bounded page)
        │  _count_persons()    -> self._fetchval(…)
        └── record_login(…)    -> BEGIN / INSERT / COMMIT       (own transaction)

"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph import exclude_graph_model
from aoa.action_machine.resources.postgres import PostgresStorage

from .identity_storage import IdentityStorage


# An implementation of IdentityStorage, the model's resource: the graph shows the resource once.
@exclude_graph_model
class IdentityPostgresStorage(IdentityStorage, PostgresStorage):
    """
    AI-CORE-BEGIN
        ROLE: The identity domain's PostgreSQL store, working through ``IdentityPool``.
        CONTRACT: ``IdentityPostgresStorage(pool=…)`` takes one connection per call; the domain's operations come from ``IdentityStorage``.
        INVARIANTS: The resource never closes the pool.
    AI-CORE-END
    """

    async def _write_login(self, person_id: str, at: str) -> None:
        """Write one login row through the driver's statement helper."""
        await self._execute(
            "INSERT INTO identity_login_event (person_id, at) VALUES ($1, $2)",
            (person_id, at),
        )

    async def _read_person(self, person_id: str) -> dict[str, Any] | None:
        """Read one person through the driver's row helper, as a plain mapping."""
        row = await self._fetchrow(
            "SELECT id, email, display_name FROM identity_person_hub WHERE id = $1",
            (person_id,),
        )
        return None if row is None else dict(row)

    async def _list_persons(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Read one ordered, bounded page of people through the driver's page helper."""
        rows = await self._fetch(
            "SELECT id, email, display_name FROM identity_person_hub ORDER BY display_name, id LIMIT $1 OFFSET $2",
            (limit, offset),
        )
        return [dict(row) for row in rows]

    async def _count_persons(self) -> int:
        """Count the people through the driver's value helper, answering the domain's number."""
        total = await self._fetchval("SELECT count(*) FROM identity_person_hub")
        return 0 if total is None else int(total)
