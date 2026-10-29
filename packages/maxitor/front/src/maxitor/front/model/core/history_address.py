# packages/maxitor/front/src/maxitor/front/model/core/history_address.py
"""
History addresses — tell a history's address from a graph's, and split off its key.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The address field takes three kinds of address, each one full URL (spec 037, FR-001):

* a private history — its port's history URL with the read key after ``#key=``:
  ``https://repo-graph-port.aoa.run/api/v1/history/orders#key=<key>``;
* a public history — a GitHub link to a graph file:
  ``https://github.com/<owner>/<repo>/blob/<branch>/<path>``;
* anything else — a running service or a graph-json address, read as today.

A history is told by the form of its address alone (FR-002). The address without its
key is the history's **name** inside Maxitor: what the page's address bar, a room and
the history store carry. The key travels apart from it, only in a header (FR-010b).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    address ──parse_history()──► PrivateHistory(port, id, key) | PublicHistory(link) | None
                     └─ out of shape ──► HistoryAddressError(reason)   (the address is never echoed)
    PrivateHistory | PublicHistory ──.name──► the address without the key
    name + key ──history_from_name()──► PrivateHistory | PublicHistory
    history + public port ──port_route()──► (the port's route, the link query or None)
    route + sha ──version_source()──► the source a version's graph is held under, keyless
    source ──parse_version_source()──► (history's name, sha) | None
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote, unquote, urlsplit

from maxitor.front.model.core.history_errors import HistoryNotFoundError

#: A port's history URL: ``<port>/api/v1/history/<id>``.
_PORT_PATH = re.compile(r"^(?P<base>.*)/api/v1/history/(?P<id>[^/]+)/?$")
#: A version's source: ``<route>/versions/<sha>`` with ``?link=`` for a public one.
_VERSION_PATH = re.compile(r"^(?P<route>.*/api/v1/history/[^/]+)/versions/(?P<sha>[0-9a-f]{7,40})$")
#: A GitHub link to a file: ``/<owner>/<repo>/blob/<branch>/<path>``.
_GITHUB_PATH = re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+[^/])$")


class HistoryAddressError(ValueError):
    """A history's address out of shape; the reason names what is wrong, never the address."""


@dataclass(frozen=True)
class PrivateHistory:
    """
    AI-CORE-BEGIN
    ROLE: A private history: the port that serves it, its id, and the read key that opens it.
    CONTRACT: ``name`` is the address without the key; ``title`` is the id; ``__repr__`` never shows the key.
    AI-CORE-END
    """

    port: str
    id: str
    key: str = field(repr=False)

    @property
    def name(self) -> str:
        """The address without the key."""
        return f"{self.port}/api/v1/history/{self.id}"

    @property
    def title(self) -> str:
        """What a person reads as the history's name."""
        return self.id


@dataclass(frozen=True)
class PublicHistory:
    """
    AI-CORE-BEGIN
    ROLE: A public history: a GitHub link to its graph file, read through Maxitor's own port.
    CONTRACT: ``name`` is the link itself; ``title`` is ``owner/repo``.
    AI-CORE-END
    """

    link: str
    owner: str
    repo: str

    @property
    def name(self) -> str:
        """The link: a public history has no key to leave out."""
        return self.link

    @property
    def title(self) -> str:
        """What a person reads as the history's name."""
        return f"{self.owner}/{self.repo}"


def parse_history(address: str) -> PrivateHistory | PublicHistory | None:
    """
    AI-CORE-BEGIN
    ROLE: Tell a history's address from any other, by its form alone (FR-002).
    CONTRACT: A port's history URL with ``#key=`` gives ``PrivateHistory``; a GitHub ``blob`` link gives ``PublicHistory``; any other address gives ``None`` (a service or a graph-json address); an address that looks like a history but is out of shape raises ``HistoryAddressError`` naming what is wrong, never the address.
    INVARIANTS: The key is everything after ``#key=``, trimmed; a second ``#`` is refused.
    AI-CORE-END
    """
    text = address.strip()
    if text.count("#") > 1:
        raise HistoryAddressError("The address has more than one '#'; a history's key follows a single '#key='.")
    base, _, fragment = text.partition("#")
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    if parts.hostname == "github.com":
        return _public(parts.path, fragment, parts.query)
    named = _PORT_PATH.match(parts.path)
    if named is None:
        return None
    if parts.query:
        raise HistoryAddressError("A history's address carries no query; give the port's history URL and '#key=<key>'.")
    if not fragment.startswith("key=") or not fragment[len("key=") :].strip():
        raise HistoryAddressError("A private history's address needs its read key after '#key='.")
    port = f"{parts.scheme}://{parts.netloc}{named.group('base')}"
    return PrivateHistory(port=port, id=unquote(named.group("id")), key=fragment[len("key=") :].strip())


def _public(path: str, fragment: str, query: str) -> PublicHistory:
    """A GitHub address: a link to a graph file, or a refusal saying what it is instead."""
    if fragment or query:
        raise HistoryAddressError("A public history's link carries no '#' and no query: give the file's GitHub link.")
    linked = _GITHUB_PATH.match(path)
    if linked is None:
        raise HistoryAddressError("A public history is a GitHub link to a graph file: https://github.com/<owner>/<repo>/blob/<branch>/<path>.")
    link = f"https://github.com{path}"
    return PublicHistory(link=link, owner=linked.group("owner"), repo=linked.group("repo"))


class PublicHistoriesNotSetUpError(ValueError):
    """Maxitor has no port of its own, so a public link cannot be read here."""

    def __init__(self) -> None:
        super().__init__("Public histories are not set up on this Maxitor")


def history_from_name(name: str, key: str) -> PrivateHistory | PublicHistory:
    """
    AI-CORE-BEGIN
    ROLE: Rebuild a history from its name (the address without the key) and the key sent apart from it.
    CONTRACT: A port's history URL with a key gives ``PrivateHistory``; a GitHub link gives ``PublicHistory``; a port's history URL with no key raises ``HistoryNotFoundError``; anything else raises ``HistoryAddressError``.
    AI-CORE-END
    """
    stripped = name.strip()
    if "#" in stripped:
        raise HistoryAddressError("A history's name carries no '#'; its key travels apart from it.")
    parts = urlsplit(stripped)
    if parts.hostname != "github.com" and _PORT_PATH.match(parts.path) is not None and not key:
        # A private history asked for with no key is refused like a wrong key: nothing tells them apart.
        raise HistoryNotFoundError()
    history = parse_history(f"{stripped}#key={key}" if parts.hostname != "github.com" else stripped)
    if history is None:
        raise HistoryAddressError("This is not a history's address.")
    return history


def port_route(history: PrivateHistory | PublicHistory, public_port: str | None) -> tuple[str, str | None]:
    """
    AI-CORE-BEGIN
    ROLE: Say where a history is read: its port's route and, for a public one, the link to pass.
    CONTRACT: A private history's route is its name; a public one's is ``<public port>/api/v1/history/public`` with its link; without a public port, a public history raises ``PublicHistoriesNotSetUpError``.
    AI-CORE-END
    """
    if isinstance(history, PrivateHistory):
        return history.name, None
    if not public_port:
        raise PublicHistoriesNotSetUpError()
    return f"{public_port.rstrip('/')}/api/v1/history/public", history.link


def version_source(route: str, link: str | None, sha: str) -> str:
    """The source a version's graph is held under: the port's version URL, never a key."""
    source = f"{route}/versions/{sha}"
    return f"{source}?link={quote(link, safe='')}" if link else source


def parse_version_source(source: str) -> tuple[str, str] | None:
    """
    AI-CORE-BEGIN
    ROLE: Tell a version's source from any other source, and name its history and commit.
    CONTRACT: Returns ``(history's name, sha)`` — the name a private history's route, or a public one's link — or ``None`` for any other source.
    AI-CORE-END
    """
    parts = urlsplit(source)
    named = _VERSION_PATH.match(parts.path)
    if named is None or parts.scheme not in ("http", "https"):
        return None
    route = f"{parts.scheme}://{parts.netloc}{named.group('route')}"
    if route.endswith("/api/v1/history/public"):
        links = parse_qs(parts.query).get("link", [])
        return (links[0], named.group("sha")) if len(links) == 1 else None
    return route, named.group("sha")
