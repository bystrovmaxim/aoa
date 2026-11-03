# packages/maxitor/web/maxitor/web/model/core/history_address.py
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

from maxitor.web.model.core.history_errors import HistoryNotFoundError

#: A port's history URL: ``<port>/api/v1/history/<id>``.
_PORT_PATH = re.compile(r"^(?P<base>.*)/api/v1/history/(?P<id>[^/]+)/?$")
#: A version's source: ``<route>/versions/<sha>`` with ``?link=`` for a public one.
_VERSION_PATH = re.compile(r"^(?P<route>.*/api/v1/history/[^/]+)/versions/(?P<sha>[0-9a-f]{7,40})$")
#: What ``quote`` leaves as it is so that a name is the same as the client's ``encodeURIComponent`` writes it.
_ENCODED_AS_THE_CLIENT = "-_.!~*'()"
#: A GitHub link to a file: ``/<owner>/<repo>/blob/<branch>/<path>``.
_GITHUB_PATH = re.compile(r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+[^/])$")


class HistoryAddressError(ValueError):
    """A history's address out of shape; the reason names what is wrong, never the address."""


@dataclass(frozen=True)
class PrivateHistory:
    """
    AI-CORE-BEGIN
    ROLE: A private history: the port that serves it, its id, and the read key that opens it.
    CONTRACT: ``name`` is the address without the key; ``title`` is the id; ``full_path`` is ``name``; ``__repr__`` never shows the key.
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

    @property
    def full_path(self) -> str:
        """What tells the history apart from another of the same name: its address without the key."""
        return self.name


@dataclass(frozen=True)
class PublicHistory:
    """
    AI-CORE-BEGIN
    ROLE: A public history: a GitHub link to its graph file, read through Maxitor's own port, optionally joined with a version file.
    CONTRACT: ``name`` is the link with ``version_link`` and ``version_key`` when given, so one graph joined with two files is two histories; ``title`` is the folder of the graph file, or ``repo`` at the root; ``full_path`` is ``owner/repo`` followed by that folder.
    AI-CORE-END
    """

    link: str
    owner: str
    repo: str
    #: The graph file's path inside the repository, as the link gives it.
    path: str
    version_link: str | None = None
    version_key: str | None = None

    @property
    def name(self) -> str:
        """The link and its version file: a public history has no key to leave out."""
        return public_name(self.link, self.version_link, self.version_key)

    @property
    def title(self) -> str:
        """What a person reads as the history's name: the graph file's folder, or the repository at the root."""
        folder = self._folder()
        return folder.rsplit("/", 1)[-1] if folder else self.repo

    @property
    def full_path(self) -> str:
        """The repository and the graph file's folder, in one path."""
        folder = self._folder()
        return f"{self.owner}/{self.repo}/{folder}" if folder else f"{self.owner}/{self.repo}"

    def _folder(self) -> str:
        """The folder that holds the graph file, empty at the repository's root."""
        return self.path.rpartition("/")[0]


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


def public_name(link: str, version_link: str | None, version_key: str | None) -> str:
    """A public history's name: its link, then its version file's parameters, always in this order."""
    parameters = [(name, value) for name, value in (("version_link", version_link), ("version_key", version_key)) if value]
    return link + ("?" + "&".join(f"{name}={quote(value, safe=_ENCODED_AS_THE_CLIENT)}" for name, value in parameters) if parameters else "")


def _first(given: dict[str, list[str]], name: str) -> str | None:
    """The first value of ``name`` in a parsed query, or ``None``."""
    values = given.get(name)
    return values[0] if values else None


def _version_parameters(query: str) -> tuple[str | None, str | None]:
    """``version_link`` and ``version_key`` of a public address; anything else is refused."""
    given = parse_qs(query, keep_blank_values=True)
    if set(given) - {"version_link", "version_key"} or any(len(values) > 1 or not values[0] for values in given.values()):
        raise HistoryAddressError("A public history's link takes only one 'version_link=' and one 'version_key=' in its query.")
    if "version_key" in given and "version_link" not in given:
        raise HistoryAddressError("'version_key=' names a key of the file in 'version_link=', so it needs one.")
    return _first(given, "version_link"), _first(given, "version_key")


def _public(path: str, fragment: str, query: str) -> PublicHistory:
    """A GitHub address: a link to a graph file, or a refusal saying what it is instead."""
    if fragment:
        raise HistoryAddressError("A public history's link carries no '#': give the file's GitHub link.")
    version_link, version_key = _version_parameters(query)
    linked = _GITHUB_PATH.match(path)
    if linked is None:
        raise HistoryAddressError("A public history is a GitHub link to a graph file: https://github.com/<owner>/<repo>/blob/<branch>/<path>.")
    link = f"https://github.com{path}"
    return PublicHistory(link=link, owner=linked.group("owner"), repo=linked.group("repo"), path=unquote(linked.group("path")), version_link=version_link, version_key=version_key)


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


def version_source(route: str, link: str | None, sha: str, version_link: str | None = None, version_key: str | None = None) -> str:
    """The source a version's graph is held under: the port's version URL, never a key."""
    source = f"{route}/versions/{sha}"
    if not link:
        return source
    joined = "".join(f"&{name}={quote(value, safe='')}" for name, value in (("version_link", version_link), ("version_key", version_key)) if value)
    return f"{source}?link={quote(link, safe='')}{joined}"


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
        given = parse_qs(parts.query)
        links = given.get("link", [])
        if len(links) != 1:
            return None
        return public_name(links[0], _first(given, "version_link"), _first(given, "version_key")), named.group("sha")
    return route, named.group("sha")
