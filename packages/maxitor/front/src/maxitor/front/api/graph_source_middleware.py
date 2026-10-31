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

A version of a history (spec 037) is read only by a reader the port lets read that history:
before such a source is acquired, ``CheckVersionAccessAction`` decides, with the read key the
request sent in ``X-Maxitor-History-Key`` — ``404`` for a key the port refuses or an unknown
version, ``422`` with the port's reason for a refused version, ``429`` and ``503`` as the port
answers. The key reaches the builder of a first build, as a header, and nothing else.

A comparison (spec 038) reads two versions: ``/api/v1/compare*`` names the newer as ``source``
and the older as ``a``. The middleware guards ``a`` exactly as it guards ``source`` — the
same key header, the same refusals, ``a`` first — and binds its entry to a second context
variable, read through ``current_base_entry``; a comparison read without ``a`` is a 400.

One request sees one entry for as long as it runs (FR-007), so a reload of the same source
in the middle of a request cannot mix two graphs in one answer. ``OPTIONS`` passes through
untouched: a CORS preflight carries no ``source`` and is answered by ``CORSMiddleware``.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import cast
from urllib.parse import parse_qsl

from maxitor.front.api.graph_store import (
    BUSY_DETAIL,
    GraphBuildError,
    GraphEntry,
    GraphStoreBusyError,
)
from maxitor.front.api.history_key_auth_coordinator import HISTORY_KEY_HEADER
from maxitor.front.model.core.actions.check_version_access_action import (
    CheckVersionAccessAction,
    CheckVersionAccessParams,
    VersionRefusedError,
)
from maxitor.front.model.core.history_address import HistoryAddressError, parse_version_source
from maxitor.front.model.core.history_errors import HistoryNotFoundError, HistoryUnreachableError, TooManyWrongKeysError
from maxitor.front.model.core.history_key_holder import HistoryKeyHolder
from maxitor.front.model.diagrams.resources.map_store import StoredVersion
from starlette.types import Receive, Scope, Send

from aoa.action_machine.context import Context, RequestInfo

#: What a read without a name is told, word for word.
MISSING_SOURCE_DETAIL = "Missing query parameter 'source': name the graph-json URL this read is for."

#: What a comparison read without its older version is told, word for word (spec 038).
MISSING_BASE_DETAIL = "Missing query parameter 'a': name the older version this comparison is from."

#: The reads that compare two versions: they name the older one as ``a`` as well.
COMPARE_PATH_PREFIX = "/api/v1/compare"

#: The reads of the map: a version with its map on disk is read with no graph built (spec 040).
MAP_PATH_PREFIX = "/api/v1/map/"

#: The pause the 503 asks a client to honour, in seconds.
RETRY_AFTER_SECONDS = 5

_CURRENT_ENTRY: ContextVar[GraphEntry | None] = ContextVar("maxitor_graph_entry", default=None)
_BASE_ENTRY: ContextVar[GraphEntry | None] = ContextVar("maxitor_base_graph_entry", default=None)
_MAP_VERSION: ContextVar[StoredVersion | None] = ContextVar("maxitor_map_version", default=None)


def current_graph_entry() -> GraphEntry | None:
    """Return the entry bound to the current request, or ``None`` outside a graph read."""
    return _CURRENT_ENTRY.get()


def current_mapped() -> GraphEntry | StoredVersion | None:
    """Return what the current read's map is read from: a stored version, or the bound entry."""
    return _MAP_VERSION.get() or _CURRENT_ENTRY.get()


def current_base_entry() -> GraphEntry | None:
    """Return the older version's entry bound to the current comparison read, or ``None`` outside one."""
    return _BASE_ENTRY.get()


def current_pair() -> tuple[GraphEntry, GraphEntry] | None:
    """The two versions the current comparison read names, A then B, or ``None`` outside one."""
    base, entry = _BASE_ENTRY.get(), _CURRENT_ENTRY.get()
    return (base, entry) if base is not None and entry is not None else None


@contextmanager
def bound_graph_entry(entry: GraphEntry, base: GraphEntry | None = None) -> Iterator[GraphEntry]:
    """Bind ``entry`` — and, for a comparison, ``base`` — to the current context for the block, then restore them."""
    token = _CURRENT_ENTRY.set(entry)
    base_token = _BASE_ENTRY.set(base)
    try:
        yield entry
    finally:
        _BASE_ENTRY.reset(base_token)
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

        source = _query_of(scope, "source")
        if not source:
            await _refuse(send, 400, MISSING_SOURCE_DETAIL)
            return

        if await self._read_stored_map(scope, receive, send, source):
            return

        base: GraphEntry | None = None
        if str(scope.get("path", "")).startswith(COMPARE_PATH_PREFIX):
            older = _query_of(scope, "a")
            if not older:
                await _refuse(send, 400, MISSING_BASE_DETAIL)
                return
            base = await _guarded(scope, send, older)
            if base is None:
                return

        entry = await _guarded(scope, send, source)
        if entry is None:
            return

        with bound_graph_entry(entry, base):
            await self._app(scope, receive, send)


    async def _read_stored_map(self, scope: Scope, receive: Receive, send: Send, source: str) -> bool:
        """Answer a map read from what is on disk, with no graph built; whether it was answered."""
        if not str(scope.get("path", "")).startswith(MAP_PATH_PREFIX):
            return False
        stored = scope["app"].state.maps.stored(source)
        if stored is None:
            return False
        if await _let_in(scope, send, source) is not None:
            token = _MAP_VERSION.set(stored)
            try:
                await self._app(scope, receive, send)
            finally:
                _MAP_VERSION.reset(token)
        return True


async def _guarded(scope: Scope, send: Send, source: str) -> GraphEntry | None:
    """The built entry of ``source`` once a version's reader is let in; ``None`` after answering the refusal."""
    key = await _let_in(scope, send, source)
    if key is None:
        return None

    store = scope["app"].state.graph_store
    try:
        return cast(GraphEntry, await store.acquire(source, key))
    except GraphStoreBusyError:
        await _refuse(send, 503, BUSY_DETAIL, retry_after=RETRY_AFTER_SECONDS)
    except GraphBuildError as exc:
        await _refuse(send, 422, exc.reason)
    return None


async def _let_in(scope: Scope, send: Send, source: str) -> str | None:
    """The read key once a version's reader is let in, empty for any other source; ``None`` after answering the refusal."""
    if parse_version_source(source) is None:
        return ""
    key = _history_key_of(scope)
    refusal = await _version_refusal(scope, source, key)
    if refusal is None:
        return key
    status, detail = refusal
    await _refuse(send, status, detail, retry_after=RETRY_AFTER_SECONDS if status == 503 else None)
    return None


def _history_key_of(scope: Scope) -> str:
    """The read key the request sent in ``X-Maxitor-History-Key``, or an empty string."""
    for name, value in scope.get("headers", []):
        if name == HISTORY_KEY_HEADER.encode("latin-1"):
            return str(value.decode("latin-1")).strip()
    return ""


async def _version_refusal(scope: Scope, source: str, key: str) -> tuple[int, str] | None:
    """Run ``CheckVersionAccessAction`` for a version's source; ``None`` when the reader may read it, else the refusal."""
    state = scope["app"].state
    client = scope.get("client")
    context = Context(user=HistoryKeyHolder(history_key=key), request=RequestInfo(client_ip=client[0] if client else None))
    try:
        await state.machine.run(context, CheckVersionAccessAction(), CheckVersionAccessParams(source=source), connections=state.history_connections)
    except (HistoryNotFoundError, HistoryAddressError):
        return 404, "not found"
    except TooManyWrongKeysError as exc:
        return 429, str(exc)
    except HistoryUnreachableError as exc:
        return 503, str(exc)
    except VersionRefusedError as exc:
        return 422, str(exc)
    return None


def _is_graph_read(scope: Scope) -> bool:
    """Return whether this request reads a graph, and so has to name its source."""
    path = str(scope.get("path", ""))
    return path == "/api/sidebar" or path.startswith("/api/v1/")


def _query_of(scope: Scope, name: str) -> str:
    """Return the query parameter ``name``, decoded and stripped, or an empty string."""
    raw = scope.get("query_string", b"")
    return (dict(parse_qsl(raw.decode("latin-1"))).get(name) or "").strip()


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
