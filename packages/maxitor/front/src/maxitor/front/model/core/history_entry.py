# packages/maxitor/front/src/maxitor/front/model/core/history_entry.py
"""
HistoryEntry — one history Maxitor holds: what its port said about it, and the keys that opened it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An open history is held once for every reader (spec 037, research R7): its description,
its versions with their ``ETag``, and when they were last checked. Its keys are kept in
memory only, newest first, so the history's freshness checks and its rooms can read it
with a key the port still accepts (research R18); they are never shown, logged or
serialised.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    OpenHistoryAction ──► HistoryEntry(name, route, link, title, repository, host, live, reader, versions, etag)
    CheckHistoryAction ──► versions, etag, live replaced; last_checked moved
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maxitor.front.model.core.history_address import version_source

#: How many hex characters of a commit name a version in an address and in a room (spec 037, FR-022).
SHORT_SHA = 12


def short_sha(sha: str) -> str:
    """The first 12 hex characters of a commit: how a version is named in an address and a room."""
    return sha[:SHORT_SHA]


@dataclass(slots=True)
class HistoryEntry:
    """
    AI-CORE-BEGIN
    ROLE: The unit ``HistoryStore`` keeps for one history.
    CONTRACT: ``name`` is the history's address without its key; ``route`` and ``link`` say where its port reads it; ``versions`` is the port's list, oldest first; ``live`` is its Live service or ``None``.
    INVARIANTS: ``keys`` never appears in ``repr``; a key is added only after the port accepted it.
    AI-CORE-END
    """

    name: str
    route: str
    link: str | None
    title: str
    repository: str
    host: str
    live: str | None
    reader: str | None
    versions: list[dict[str, Any]]
    etag: str | None
    last_read: float = 0.0
    last_checked: float = 0.0
    checking: bool = False
    keys: list[str] = field(default_factory=list, repr=False)

    def remember(self, key: str) -> None:
        """Keep ``key`` as the newest one the port accepted for this history."""
        if not key:
            return
        if key in self.keys:
            self.keys.remove(key)
        self.keys.insert(0, key)

    def forget(self, key: str) -> None:
        """Drop ``key``, which the port no longer accepts."""
        if key in self.keys:
            self.keys.remove(key)

    def version(self, sha: str) -> dict[str, Any] | None:
        """The version whose commit starts with ``sha``, or ``None``."""
        if len(sha) < 7:
            return None
        return next((version for version in self.versions if str(version.get("sha", "")).startswith(sha)), None)

    def default_version(self) -> str | None:
        """
        The version a history opens on (spec 037, FR-021): ``live`` when it has Live; otherwise its
        newest version not refused, or its newest when every one is; ``None`` when it has none (M7).
        """
        if self.live:
            return "live"
        usable = [version for version in self.versions if not version.get("refused")] or self.versions
        return short_sha(str(usable[-1]["sha"])) if usable else None

    def offers(self, version: str) -> bool:
        """Whether ``version`` (a short sha or ``live``) can be shown: listed and not refused, or Live where there is Live."""
        if version == "live":
            return bool(self.live)
        found = self.version(version)
        return found is not None and not found.get("refused")

    def source_of(self, version: str) -> str | None:
        """The graph source of ``version``: Live's address, or the port's version URL with the full commit; ``None`` when it cannot be shown."""
        if not self.offers(version):
            return None
        if version == "live":
            return self.live
        found = self.version(version)
        return version_source(self.route, self.link, str(found["sha"])) if found is not None else None

    def versions_with_sources(self) -> list[dict[str, Any]]:
        """The versions as a tab is told them: each with the ``source`` its graph is read under, keyless."""
        return [{**version, "source": version_source(self.route, self.link, str(version["sha"]))} for version in self.versions]

    @property
    def public(self) -> bool:
        """Whether the history is read by a public link, with no key."""
        return self.link is not None
