# packages/maxitor/front/src/maxitor/front/api/graph_source_middleware.py
"""
GraphSourceMiddleware — turn the ``source`` of a graph read into that read's built graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every diagram read and the sidebar read name the AOA service whose graph they want, as
``?source=<graph-json URL>``. Until #214 nothing named it: the request read whatever one
shared slot held, so two users overwrote each other. This middleware makes the name
authoritative. It runs before the adapter or the sidebar route, asks the ``GraphStore`` for
that source (building it on a cold read, once however many readers arrive), and binds the
resulting entry to the request through a context variable.

The refusal is answered here, not inside an action, on purpose: a failure raised inside an
action reaches the caller as the adapter's generic ``500 {"detail": "Internal server
error"}``, and a caller needs to know whether the address is missing, unbuildable, or the
stand is merely busy. Hence three named answers — 400, 422, 503 — each with the reason.

The 503 carries ``Retry-After: 5`` and the answer is wrapped by ``CORSMiddleware`` (this
middleware is installed inside it), so the header travels with ``Access-Control-Allow-Origin``
and ``Access-Control-Expose-Headers``; a client served from another origin can therefore
read the pause instead of retrying on its own guess.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/full-graph?source=…     GET /api/sidebar?source=…
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
                     GraphSourceMiddleware
                                │  missing/blank ──► 400 {"detail": "Missing …"}
                                │  unbuildable   ──► 422 {"detail": <reason>}
                                │  no build slot ──► 503 {"detail": …} + Retry-After
                                ▼
                  store.acquire(source) ──► GraphEntry
                                │
                                ▼
              ContextVar for this request only (reset in finally)
                       │                        │
                       ▼                        ▼
        DuckDBGraphHolder._resolve()   GET /api/sidebar
                       │                        │
                       ▼                        ▼
                 entry.graph                entry.sidebar

One request sees one entry for as long as it runs (FR-007), so a reload of the same source
in the middle of a request cannot mix two graphs in one answer. ``OPTIONS`` passes through
untouched: a CORS preflight carries no ``source`` and is answered by ``CORSMiddleware``.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import parse_qsl

from maxitor.front.api.graph_store import (
    BUSY_DETAIL,
    GraphBuildError,
    GraphEntry,
    GraphStoreBusyError,
)
from starlette.types import Receive, Scope, Send

#: What a read without a name is told, word for word.
MISSING_SOURCE_DETAIL = "Missing query parameter 'source': name the graph-json URL this read is for."

#: The pause the 503 asks a client to honour, in seconds.
RETRY_AFTER_SECONDS = 5

_CURRENT_ENTRY: ContextVar[GraphEntry | None] = ContextVar("maxitor_graph_entry", default=None)


def current_graph_entry() -> GraphEntry | None:
    """Return the entry bound to the current request, or ``None`` outside a graph read."""
    return _CURRENT_ENTRY.get()


@contextmanager
def bound_graph_entry(entry: GraphEntry) -> Iterator[GraphEntry]:
    """Bind ``entry`` to the current context for the duration of the block, then restore it."""
    token = _CURRENT_ENTRY.set(entry)
    try:
        yield entry
    finally:
        _CURRENT_ENTRY.reset(token)


class GraphSourceMiddleware:
    """
    Bind every graph read to the graph of the source it names.

    AI-CORE-BEGIN
    ROLE: The request-level step that turns ``?source=`` into one built entry for that request.
    CONTRACT: ``/api/v1/*`` and ``/api/sidebar`` get 400 without a source, 422 when it cannot be
    built, 503 when no build slot frees within the wait limit; anything else passes untouched.
    INVARIANTS: One entry per request; the entry is read through ``current_graph_entry``, never
    from application state; the binding is reset even when the endpoint raises.
    AI-CORE-END
    """

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Guard a graph read with its source, bind the entry, and delegate the answer."""
        if scope["type"] != "http" or not _is_graph_read(scope) or scope.get("method") == "OPTIONS":
            await self._app(scope, receive, send)
            return

        source = _source_of(scope)
        if not source:
            await _refuse(send, 400, MISSING_SOURCE_DETAIL)
            return

        store = scope["app"].state.graph_store
        try:
            entry = await store.acquire(source)
        except GraphStoreBusyError:
            await _refuse(send, 503, BUSY_DETAIL, retry_after=RETRY_AFTER_SECONDS)
            return
        except GraphBuildError as exc:
            await _refuse(send, 422, exc.reason)
            return

        with bound_graph_entry(entry):
            await self._app(scope, receive, send)


def _is_graph_read(scope: Scope) -> bool:
    """Return whether this request reads a graph, and so has to name its source."""
    path = str(scope.get("path", ""))
    return path == "/api/sidebar" or path.startswith("/api/v1/")


def _source_of(scope: Scope) -> str:
    """Return the ``source`` query parameter, decoded and stripped, or an empty string."""
    raw = scope.get("query_string", b"")
    return (dict(parse_qsl(raw.decode("latin-1"))).get("source") or "").strip()


async def _refuse(send: Send, status: int, detail: str, *, retry_after: int | None = None) -> None:
    """Answer with the named refusal the contract promises, before any action runs."""
    body = json.dumps({"detail": detail}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if retry_after is not None:
        headers.append((b"retry-after", str(retry_after).encode("ascii")))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
