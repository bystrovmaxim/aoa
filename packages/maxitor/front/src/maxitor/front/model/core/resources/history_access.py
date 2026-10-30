# packages/maxitor/front/src/maxitor/front/model/core/resources/history_access.py
"""
HistoryAccess — which keys a port accepted lately, and the tickets that let a tab into a room.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A version's graph is built once and shared by every reader of it (spec 037, FR-005), but
only a reader whose key the port accepts may read it (FR-009). Asking the port on every
diagram read would cost a round trip per read, so this resource remembers, by the key's
SHA-256, when the port last accepted a key for a history; an acceptance stays good for
30 seconds — the freshness interval — so a revoked key stops working within one check
(research R6).

A browser cannot put a header on a WebSocket, and the key must never be in a URL
(FR-010b). A tab that opened a private history therefore gets a room ticket: 128 random
bits, good for 60 seconds and one use, bound to the history and the key's SHA-256. The
ticket, not the key, travels on the room's socket (research R18).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    port accepted (name, key) ──accept()──► {(name, sha256(key)): when}
    accepted(name, key)? ──► within 30 s?
    issue_ticket(name, key) ──► ticket ──redeem(ticket, name)──► sha256(key) | None   (once, within 60 s)
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections.abc import Callable

from maxitor.front.model.core.core_domain import CoreDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Connection key under which actions receive the resource.
HISTORY_ACCESS_CONNECTION_KEY = "HistoryAccess"
#: How long a port's acceptance of a key stands without asking again.
ACCEPTED_FOR_SECONDS = 30.0
#: How long a room ticket may wait to be used.
TICKET_SECONDS = 60.0


def key_digest(key: str) -> str:
    """The SHA-256 of ``key``, the only form this resource keeps."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@meta(description="Which keys a port accepted lately, and room tickets", domain=CoreDomain)
class HistoryAccess(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: Remember the port's recent answers about keys, and hand out one-use room tickets.
    CONTRACT: ``accepted`` is true for 30 s after ``accept``; ``forget`` ends it at once; ``redeem`` returns the key's SHA-256 for a ticket issued for that history within 60 s, once.
    INVARIANTS: Keeps hashes of keys, never a key; ``repr`` shows nothing.
    AI-CORE-END
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._accepted: dict[tuple[str, str], float] = {}
        self._tickets: dict[str, tuple[str, str, float]] = {}
        self._clock = clock

    def __repr__(self) -> str:
        """Show nothing of what is held."""
        return "HistoryAccess()"

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same resource."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory resource is not a rollup target."""
        return False

    def accept(self, name: str, key: str) -> None:
        """Record that the port accepted ``key`` for history ``name`` now."""
        self._accepted[(name, key_digest(key))] = self._clock()

    def accepted(self, name: str, key: str) -> bool:
        """Whether the port accepted ``key`` for ``name`` within the last 30 seconds."""
        when = self._accepted.get((name, key_digest(key)))
        return when is not None and self._clock() - when <= ACCEPTED_FOR_SECONDS

    def forget(self, name: str, key: str) -> None:
        """Drop the port's acceptance of ``key`` for ``name``: it refused it."""
        self._accepted.pop((name, key_digest(key)), None)

    def issue_ticket(self, name: str, key: str) -> str:
        """A one-use ticket that lets a tab holding ``key`` into a room of ``name`` within 60 s."""
        now = self._clock()
        for ticket in [t for t, (_, _, issued) in self._tickets.items() if now - issued > TICKET_SECONDS]:
            del self._tickets[ticket]
        ticket = secrets.token_urlsafe(16)
        self._tickets[ticket] = (name, key_digest(key), now)
        return ticket

    def redeem(self, ticket: str, name: str) -> str | None:
        """The key's SHA-256 for a valid ``ticket`` of ``name``, used up; ``None`` for any other."""
        held = self._tickets.pop(ticket, None)
        if held is None:
            return None
        history, digest, issued = held
        if history != name or self._clock() - issued > TICKET_SECONDS:
            return None
        return digest
