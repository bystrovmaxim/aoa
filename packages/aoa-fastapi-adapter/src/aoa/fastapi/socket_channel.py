# packages/aoa-fastapi-adapter/src/aoa/fastapi/socket_channel.py
"""
SocketChannel — one WebSocket connection, as a resource an action can send through.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A WebSocket route runs an action for every message it receives. Those actions,
and the resources they use, need a way to send events back to this client and
to other clients — without touching the transport themselves. ``SocketChannel``
is that way: the adapter creates one per connection and hands it to every action
of the route as ``connections["socket"]``.

Two kinds of sending exist, because a slow client must never hold the others up:

- **durable** events (``send``) reach the client in the order they were sent;
  when too many are waiting, the client is too slow and its connection is closed;
- **volatile** events (``send_volatile``) keep only the newest value per kind —
  a pointer position, a screen position — so a slow client gets the latest one,
  never a backlog.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action / resource ──send(event)──────────────► ordered queue (≤ max_pending)
                      ──send_volatile(kind, e)──► one slot per kind (newest wins)
                                                          │
                                          wake ───────────┘
                                                          ▼
                                   writer task (one per channel) ──► websocket
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from collections import deque
from collections.abc import Mapping
from typing import Any

from starlette.websockets import WebSocket

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Close code sent when a client cannot keep up with its durable events.
CLIENT_TOO_SLOW = 4008


class TransportDomain(BaseDomain):
    """Domain of the transport resources the FastAPI adapter hands to actions."""

    name = "transport"
    description = "Resources the FastAPI adapter creates for one connection"


@meta(description="One WebSocket connection an action can send events through", domain=TransportDomain)
class SocketChannel(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: The per-connection resource through which actions and resources send events to one client.
    CONTRACT: ``send`` keeps order and closes a client that falls ``max_pending`` events behind;
    ``send_volatile`` keeps only the newest event per kind; nothing is sent after ``close``.
    INVARIANTS: One channel per connection, one writer task per channel; the channel decides nothing
    about what is sent or to whom.
    AI-CORE-END
    """

    def __init__(self, websocket: WebSocket, *, max_pending: int = 256) -> None:
        self.id: str = secrets.token_urlsafe(8)
        self._websocket = websocket
        self._max_pending = max_pending
        self._ordered: deque[Mapping[str, Any]] = deque()
        self._volatile: dict[str, Mapping[str, Any]] = {}
        self._wake = asyncio.Event()
        self._close_request: tuple[int, str] | None = None
        self._closed = False

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions send through this same channel."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that a connection is not a rollup target."""
        return False

    @property
    def closed(self) -> bool:
        """Whether the connection has ended or is being closed."""
        return self._closed or self._close_request is not None

    def send(self, event: Mapping[str, Any]) -> None:
        """Queue a durable event; close the connection when the client is ``max_pending`` behind."""
        if self.closed:
            return
        if len(self._ordered) >= self._max_pending:
            self._request_close(CLIENT_TOO_SLOW, "client too slow")
            return
        self._ordered.append(event)
        self._wake.set()

    def send_volatile(self, kind: str, event: Mapping[str, Any]) -> None:
        """Replace the pending event of ``kind``, if any, with ``event``."""
        if self.closed:
            return
        self._volatile[kind] = event
        self._wake.set()

    def close(self, code: int, reason: str) -> None:
        """Ask for the connection to be closed with ``code`` and ``reason``."""
        self._request_close(code, reason)

    def _request_close(self, code: int, reason: str) -> None:
        """Remember the first close request and wake the writer to carry it out."""
        if self._close_request is None and not self._closed:
            self._close_request = (code, reason)
        self._wake.set()

    async def run_writer(self) -> None:
        """Send queued events until the connection ends; carry out a close request."""
        try:
            while not self._closed:
                await self._wake.wait()
                self._wake.clear()
                while self._ordered and self._close_request is None:
                    await self._websocket.send_json(self._ordered.popleft())
                for kind in list(self._volatile):
                    if self._close_request is not None:
                        break
                    await self._websocket.send_json(self._volatile.pop(kind))
                if self._close_request is not None:
                    code, reason = self._close_request
                    self._closed = True
                    with contextlib.suppress(Exception):
                        await self._websocket.close(code=code, reason=reason)
        finally:
            self._closed = True

    def mark_closed(self) -> None:
        """Record that the connection ended from the other side; wake the writer so it stops."""
        self._closed = True
        self._wake.set()
