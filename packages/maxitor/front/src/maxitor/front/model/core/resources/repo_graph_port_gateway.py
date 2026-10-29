# packages/maxitor/front/src/maxitor/front/model/core/resources/repo_graph_port_gateway.py
"""
RepoGraphPortGateway — the one way Maxitor asks a port about a history.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history is read only through a ``repo-graph-port`` (spec 037, FR-003): a private one
through the port its address names, a public one through Maxitor's own port. Every
request to a port goes through this resource, so the actions decide what an answer
means while the resource only asks. The read key is sent in the header
``X-Maxitor-History-Key`` and nowhere else (FR-010b); the resource keeps no key and
names none in its representation. An answer is a typed value, never an exception: a
port that refuses, blocks or does not answer is an outcome an action must handle.

Maxitor's own port, for public links, is given to the resource where the app is built
(``MAXITOR_PUBLIC_PORT``), never read in an action (FR-003b).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action aspect ──describe(route, link, key)──► GET <route>[?link=]
                 ──versions(route, link, key, etag)──► GET <route>/versions[?link=], If-None-Match
                                    │
           Described | Listed | PortNotModified | PortNotFound | PortTooManyWrongKeys | PortUnreachable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from maxitor.front.model.core.core_domain import CoreDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_gateway import BaseGateway

#: Connection key under which actions receive the gateway.
REPO_GRAPH_PORT_CONNECTION_KEY = "RepoGraphPort"
#: How long one request to a port may take before it counts as not answering.
PORT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class Described:
    """A history's description, as the port's ``describe`` answered it."""

    body: dict[str, Any]


@dataclass(frozen=True)
class Listed:
    """A history's versions, oldest first, with the ``ETag`` of that list."""

    versions: list[dict[str, Any]]
    etag: str | None


@dataclass(frozen=True)
class PortNotModified:
    """The port answered ``304``: the list held for the ``ETag`` sent is still current."""


@dataclass(frozen=True)
class PortNotFound:
    """The port answered ``404``: a wrong key, an unknown history — the port does not say which."""


@dataclass(frozen=True)
class PortTooManyWrongKeys:
    """The port answered ``429``: it blocks this Maxitor for a minute."""


@dataclass(frozen=True)
class PortUnreachable:
    """No usable answer; ``reason`` names the cause, never an address or a key."""

    reason: str


@meta(description="Asks a repo-graph-port about a history", domain=CoreDomain)
class RepoGraphPortGateway(BaseGateway):
    """
    AI-CORE-BEGIN
    ROLE: The gateway through which Maxitor's actions read a history from its port.
    CONTRACT: ``describe`` and ``versions`` return a typed answer for every outcome and never raise for a refusal or a failure; ``public_port`` is Maxitor's own port, or ``None`` when public links are not set up.
    INVARIANTS: The key goes only in the ``X-Maxitor-History-Key`` header; nothing is kept; ``repr`` names nothing.
    AI-CORE-END
    """

    def __init__(self, public_port: str | None = None, *, timeout: float = PORT_TIMEOUT_SECONDS, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.public_port = public_port or None
        self._timeout = timeout
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    def __repr__(self) -> str:
        """Name the gateway only: never a port's address or a key."""
        return "RepoGraphPortGateway()"

    def get_wrapper_class(self) -> type[BaseGateway] | None:
        """Return ``None``: nested actions read through this same gateway."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that a read is not a rollup target."""
        return False

    async def describe(self, route: str, link: str | None, key: str) -> Described | PortNotFound | PortTooManyWrongKeys | PortUnreachable:
        """Ask the port what the history is."""
        answer = await self._get(route, link, key, None)
        if isinstance(answer, httpx.Response):
            body = _json_object(answer)
            return Described(body) if body is not None else PortUnreachable("the port's description is not a JSON object")
        if isinstance(answer, PortNotModified):
            return PortUnreachable("the port answered 304 to a request without a tag")
        return answer

    async def versions(self, route: str, link: str | None, key: str, etag: str | None) -> Listed | PortNotModified | PortNotFound | PortTooManyWrongKeys | PortUnreachable:
        """Ask the port for the history's versions; ``PortNotModified`` when ``etag`` is still current."""
        answer = await self._get(f"{route}/versions", link, key, etag)
        if not isinstance(answer, httpx.Response):
            return answer
        body = _json_object(answer)
        listed = body.get("versions") if body is not None else None
        if not isinstance(listed, list):
            return PortUnreachable("the port's list of versions is not a list")
        return Listed([version for version in listed if isinstance(version, dict)], answer.headers.get("etag"))

    async def _get(self, url: str, link: str | None, key: str, etag: str | None) -> httpx.Response | PortNotModified | PortNotFound | PortTooManyWrongKeys | PortUnreachable:
        """One GET to a port, turned into a response or a typed outcome."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
        headers = {"X-Maxitor-History-Key": key} if key else {}
        if etag:
            headers["If-None-Match"] = etag
        try:
            response = await self._client.get(url, params={"link": link} if link else None, headers=headers)
        except httpx.RequestError as exc:
            return PortUnreachable(type(exc).__name__)
        if response.status_code == 304:
            return PortNotModified()
        if response.status_code == 404:
            return PortNotFound()
        if response.status_code == 429:
            return PortTooManyWrongKeys()
        if response.is_error:
            return PortUnreachable(f"HTTP {response.status_code}")
        return response

    async def aclose(self) -> None:
        """Close the HTTP client, when one was opened."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    """The response's body as a JSON object, or ``None``."""
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None
