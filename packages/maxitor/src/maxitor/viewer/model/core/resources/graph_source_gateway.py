# packages/maxitor/src/maxitor/viewer/model/core/resources/graph_source_gateway.py
"""
GraphSourceGateway — the one way Maxitor downloads an AOA service's ``graph-json``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An AOA service is an external service: Maxitor asks it for its graph and does not own
it. Every request to it goes through this resource, never through ``httpx`` in an
aspect, so the actions that build or check a graph decide what an answer means while
the resource only fetches it. An answer is a typed value, never an exception: a
service that is down, slow or answering with an error is a normal outcome an action
must handle, not a crash.

The body is returned with what identifies it — its SHA-256 and the validators the
service gave (``ETag``, ``Last-Modified``) — because a held graph remembers them to
know later whether its source changed.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action aspect ──fetch(url)──► GraphSourceGateway ──GET──► AOA service
                                         │
                       Document(body, sha256, etag, last_modified)
                     | Unreachable(reason, status)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx
from maxitor.viewer.model.core.core_domain import CoreDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_gateway import BaseGateway

#: Connection key under which actions receive the gateway.
GRAPH_SOURCE_CONNECTION_KEY = "GraphSource"

#: How long one download may take before the service counts as unreachable.
FETCH_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class Document:
    """A ``graph-json`` body as the service sent it, with what identifies it."""

    body: bytes
    sha256: str
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True)
class NotModified:
    """The service answered ``304``: the body held for the validators sent is still current."""


@dataclass(frozen=True)
class Unreachable:
    """No usable answer: the service answered an HTTP error (``status``) or could not be reached."""

    reason: str
    status: int | None = None


@meta(description="Downloads an AOA service's graph-json", domain=CoreDomain)
class GraphSourceGateway(BaseGateway):
    """
    AI-CORE-BEGIN
    ROLE: The gateway through which Maxitor's actions download a ``graph-json`` document.
    CONTRACT: ``fetch`` returns ``Document`` for a 2xx answer and ``Unreachable`` for an HTTP error,
    a timeout or a network failure; ``fetch_if_changed`` also returns ``NotModified`` for a ``304`` to
    the validators it was given. Neither raises for those.
    INVARIANTS: One HTTP client per gateway, created on first use and closed by ``aclose``; the
    gateway keeps no answers and decides nothing about them.
    AI-CORE-END
    """

    def __init__(self, *, timeout: float = FETCH_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def get_wrapper_class(self) -> type[BaseGateway] | None:
        """Return ``None``: nested actions download through this same gateway."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that a download is not a rollup target."""
        return False

    async def fetch(self, url: str) -> Document | Unreachable:
        """Download ``url``; return the body with its SHA-256 and validators, or why there is none."""
        answer = await self._get(url, {})
        # Without validators a service has nothing to answer 304 to.
        return Unreachable(reason="HTTP 304 to an unconditional request", status=304) if isinstance(answer, NotModified) else answer

    async def fetch_if_changed(self, url: str, etag: str | None, last_modified: str | None) -> Document | NotModified | Unreachable:
        """
        Ask ``url`` again with the validators of the body held: ``NotModified`` when the service
        confirms it, the new ``Document`` when it changed, or why there is no answer.
        """
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        return await self._get(url, headers)

    async def _get(self, url: str, headers: dict[str, str]) -> Document | NotModified | Unreachable:
        """One GET of ``url`` with ``headers``, turned into a typed answer."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await self._client.get(url, headers=headers)
        except httpx.RequestError as exc:
            return Unreachable(reason=str(exc) or type(exc).__name__)
        if response.status_code == 304:
            return NotModified()
        if response.is_error:
            return Unreachable(reason=f"HTTP {response.status_code}", status=response.status_code)
        body = response.content
        return Document(
            body=body,
            sha256=hashlib.sha256(body).hexdigest(),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    async def aclose(self) -> None:
        """Close the HTTP client, when one was opened."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
