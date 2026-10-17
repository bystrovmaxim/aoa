# packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_base.py
"""
IdentityStoreBase — what the identity domain asks of its store, driver-free.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The identity domain needs exactly two things from storage: read one person, and
record one login inside a transaction. This class states those two, in terms of
the SQL contract the framework already defines, and leaves the storage primitive
to whoever implements it:

* ``IdentityStore`` (PostgreSQL) mixes this with ``PostgresResource`` and reads
  rows from the connection the framework hands over;
* ``IdentityStoreStub`` keeps the same two behaviours in memory, so the demo runs
  with no database and with no driver installed.

Nothing here imports a driver. That is the point: the driver is needed to create
the pool and not to describe the domain, so the demo stays importable without the
``postgres`` extra.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    IdentityStoreBase (SqlResource)
        │  read_person(id)      -> _read_person(id)
        │  record_login(id, at) -> begin / _write_login / commit, rollback on failure
        │
        ├── IdentityStore      (+ PostgresResource)  pool-backed, real driver
        └── IdentityStoreStub  (in-memory)           database-free mode

"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlResource

from ..domain import IdentityDomain


@meta(description="Identity store: read a person, record a login", domain=IdentityDomain)
class IdentityStoreBase(SqlResource):
    """
    AI-CORE-BEGIN
        ROLE: The identity domain's storage semantics, independent of any driver.
        CONTRACT: ``read_person`` answers one person or nothing through ``_read_person``; ``record_login`` owns one transaction and rolls it back on any failure.
        INVARIANTS: No driver is imported here; an implementation supplies the storage primitive and the lifecycle.
    AI-CORE-END
    """

    @abstractmethod
    async def _read_person(self, person_id: str) -> dict[str, Any] | None:
        """Read one person; the implementation decides how it reads them."""

    @abstractmethod
    async def _write_login(self, person_id: str, at: str) -> None:
        """Record one login; the implementation decides how it writes it."""

    async def read_person(self, person_id: str) -> dict[str, Any] | None:
        """Return the person, or nothing when nobody matches."""
        return await self._read_person(person_id)

    async def record_login(self, person_id: str, at: str) -> None:
        """Record one login inside a transaction this method opens and ends."""
        await self.begin()
        try:
            await self._write_login(person_id, at)
        except BaseException:  # a failed or cancelled unit of work still ends its transaction
            await self.rollback()
            raise
        await self.commit()
