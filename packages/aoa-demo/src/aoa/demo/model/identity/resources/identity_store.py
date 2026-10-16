# packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store.py
"""
IdentityStore — the identity domain over PostgreSQL, one connection per call.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This is the resource the demo route declares per call: ``IdentityStore(pool=…)``
borrows one connection from the application's pool in ``open()`` and gives it
back in ``close()``, so two concurrent calls never share a session. The domain's
two operations come from ``IdentityStoreBase``; the storage primitive is the
connection the framework handed over.

Importing this module needs the ``postgres`` extra, because ``PostgresResource``
imports the driver. That is why the demo reaches for it lazily — inside the
factory that builds the resource — and never at import time.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    IdentityStore(IdentityStoreBase, PostgresResource)
        │  open()/close()      -> pool.acquire / pool.release   (once per call)
        │  read_person(id)     -> self._conn.fetch(…)
        └── record_login(…)    -> BEGIN / INSERT / COMMIT       (own transaction)

"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

from .identity_store_base import IdentityStoreBase


class IdentityStore(IdentityStoreBase, PostgresResource):
    """
    AI-CORE-BEGIN
        ROLE: The identity domain's PostgreSQL store, built from a pool.
        CONTRACT: ``IdentityStore(pool=…)`` borrows one connection per call; the domain's operations come from ``IdentityStoreBase``.
        INVARIANTS: The wait bound is stated on the class, not inherited silently; the resource never closes the pool.
    AI-CORE-END
    """

    acquire_timeout: float | None = 30.0
    """How long this resource waits for a free connection before it fails, stated here for the reader."""

    async def _write_login(self, person_id: str, at: str) -> None:
        """Write one login row through the driver's statement helper."""
        await self._execute(
            "INSERT INTO identity_login_event (person_id, at) VALUES ($1, $2)",
            (person_id, at),
        )

    async def _fetch_rows(self, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Read rows from this call's own connection."""
        if self._conn is None:
            raise RuntimeError("IdentityStore is not open: call open() first.")
        rows = await self._conn.fetch(query, *params)
        return [dict(row) for row in rows]
