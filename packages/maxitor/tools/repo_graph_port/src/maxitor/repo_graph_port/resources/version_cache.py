# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/resources/version_cache.py
"""
VersionCache — what never changes for a commit, kept on disk; when a repository was last fetched.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A version's graph file and the facts read from it — its counts, or why it is
refused — belong to its commit and never change. They are read from git once and
kept, so a second read of a version touches neither git nor the file again. The
cache also remembers when each repository's mirror was last fetched, so a history
fetches again only after the fallback interval, and what the host said about each
version's pull request and each tag's release, with when it said it: those can
change, so they are read again after a webhook or the fallback interval.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    <folder>/versions/<repository key>/<sha>.graph  — the file's bytes
    <folder>/versions/<repository key>/<sha>.json   — {"nodes", "edges", "refused"}

The repository key is the first 16 hex of the SHA-256 of the repository's name, so
any name — ``owner/name`` or a local path — is one safe folder. A file is written
to a temporary name and renamed, so a reader never sees half of one. The fetch
times, pull requests and releases live in memory: after a restart every repository
is fetched, and every pull request and release read, on its first read.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


@meta(description="A version's graph and facts on disk, by commit; when each repository was fetched", domain=RepoGraphDomain)
class VersionCache(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: Keep what never changes for a commit, and when each repository was last fetched.
    CONTRACT: ``keep`` stores a version's bytes and facts by ``(repository, sha)``; ``graph`` and ``facts`` return them, or ``None`` before ``keep``; ``fetched_at`` returns the time ``mark_fetched`` was given, or ``None``; pull requests and releases are kept with their read time until forgotten.
    INVARIANTS: Kept entries are never changed or removed; a reader never sees a half-written file.
    AI-CORE-END
    """

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._fetched: dict[str, float] = {}
        self._pulls: dict[tuple[str, str], tuple[dict[str, str | int] | None, float]] = {}
        self._releases: dict[tuple[str, str], tuple[dict[str, str] | None, float]] = {}

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same cache."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the cache is not a rollup target."""
        return False

    def keep(self, repository: str, sha: str, content: bytes, facts: GraphFacts) -> None:
        """Store a version's file and its facts for good."""
        place = self._place(repository)
        place.mkdir(parents=True, exist_ok=True)
        _write(place / f"{sha}.graph", content)
        _write(place / f"{sha}.json", json.dumps({"nodes": facts.nodes, "edges": facts.edges, "refused": facts.refused}).encode())

    def graph(self, repository: str, sha: str) -> bytes | None:
        """A kept version's file, or ``None``."""
        try:
            return (self._place(repository) / f"{sha}.graph").read_bytes()
        except FileNotFoundError:
            return None

    def facts(self, repository: str, sha: str) -> GraphFacts | None:
        """A kept version's facts, or ``None``."""
        try:
            kept = json.loads((self._place(repository) / f"{sha}.json").read_bytes())
        except FileNotFoundError:
            return None
        return GraphFacts(nodes=kept["nodes"], edges=kept["edges"], refused=kept["refused"])

    def pull_request(self, repository: str, sha: str) -> tuple[dict[str, str | int] | None, float] | None:
        """A version's pull request as last read (``None`` when it had none) and when it was read; ``None`` before any read."""
        return self._pulls.get((repository, sha))

    def keep_pull_request(self, repository: str, sha: str, pull: dict[str, str | int] | None, at: float) -> None:
        """Remember a version's pull request, read at ``at``."""
        self._pulls[(repository, sha)] = (pull, at)

    def forget_pull_request(self, repository: str, sha: str) -> None:
        """Drop a version's pull request, so the next read asks the host again."""
        self._pulls.pop((repository, sha), None)

    def release(self, repository: str, tag: str) -> tuple[dict[str, str] | None, float] | None:
        """A tag's release as last read (``None`` when it had none) and when it was read; ``None`` before any read."""
        return self._releases.get((repository, tag))

    def keep_release(self, repository: str, tag: str, release: dict[str, str] | None, at: float) -> None:
        """Remember a tag's release, read at ``at``."""
        self._releases[(repository, tag)] = (release, at)

    def forget_releases(self, repository: str) -> None:
        """Drop every release of ``repository``, so the next read asks the host again."""
        for key in [key for key in self._releases if key[0] == repository]:
            del self._releases[key]

    def fetched_at(self, repository: str) -> float | None:
        """When ``repository`` was last fetched, as given to ``mark_fetched``, or ``None``."""
        return self._fetched.get(repository)

    def mark_fetched(self, repository: str, at: float) -> None:
        """Remember that ``repository`` was fetched at ``at``."""
        self._fetched[repository] = at

    def _place(self, repository: str) -> Path:
        """The folder of one repository's versions."""
        return self._folder / "versions" / hashlib.sha256(repository.encode()).hexdigest()[:16]


def _write(target: Path, content: bytes) -> None:
    """Write ``content`` to a temporary file beside ``target`` and rename it into place."""
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    with os.fdopen(handle, "wb") as out:
        out.write(content)
    os.replace(temporary, target)
