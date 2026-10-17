# packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_stub.py
"""
IdentityStoreStub — the same identity store, in memory, with no database.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The demo must start and answer with no PostgreSQL running and no driver
installed. This stub keeps ``IdentityStoreBase``'s two operations and replaces
the storage primitive with two dictionaries, so the route, the action and the
lifecycle are exactly the ones a reader copies — only the storage differs.

It imports no driver and holds no connection, so its ``close()`` is the
contract's harmless default.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    IdentityStoreStub(IdentityStoreBase)
        │  open()/close()  -> nothing to acquire, nothing to release
        │  _read_person/_write_login -> the two dicts below are the storage
        ├── people:  id -> {"id", "email", "display_name"}
        └── logins:  the base class's transaction writes here

"""

from __future__ import annotations

from typing import Any

from .identity_store_base import IdentityStoreBase


class IdentityStoreStub(IdentityStoreBase):
    """
    AI-CORE-BEGIN
        ROLE: Database-free stand-in for the identity store.
        CONTRACT: Same two operations as the real store; rows come from an in-memory table seeded on first use.
        INVARIANTS: No driver, no connection; the write primitive appends to a list in memory.
    AI-CORE-END
    """

    def __init__(self) -> None:
        """Seed one person so the route answers something useful out of the box."""
        super().__init__()
        self.people: dict[str, dict[str, Any]] = {
            "person-1": {"id": "person-1", "email": "person-1@example.test", "display_name": "Person One"},
        }
        self.logins: list[dict[str, str]] = []

    async def open(self) -> None:
        """Nothing to acquire: the two dictionaries are always there."""

    async def begin(self) -> None:
        """No transaction to open in memory."""

    async def commit(self) -> None:
        """No transaction to commit in memory."""

    async def rollback(self) -> None:
        """No transaction to roll back in memory."""

    async def _write_login(self, person_id: str, at: str) -> None:
        """Append one login to the in-memory list."""
        self.logins.append({"person_id": str(person_id), "at": str(at)})

    async def _read_person(self, person_id: str) -> dict[str, Any] | None:
        """Answer the person lookup from memory."""
        person = self.people.get(str(person_id))
        return None if person is None else dict(person)
