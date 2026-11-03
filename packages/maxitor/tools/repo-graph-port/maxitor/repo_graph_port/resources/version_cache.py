# packages/maxitor/tools/repo-graph-port/maxitor/repo_graph_port/resources/version_cache.py
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
version's pull request, each tag's release and the pull requests still open, with
when it said it: those can change, so they are read again after a webhook or the
fallback interval.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    <folder>/graphs/<repository key>/<graph key>/<sha>.graph  — the file's bytes
    <folder>/graphs/<repository key>/<graph key>/<sha>.json   — {"nodes", "edges", "refused"}
    <folder>/graphs/<repository key>/<graph key>/<sha>.detail.json — who made it, its size, what it did to the graph
    <folder>/numbers/<repository key>/<file and key>/<sha>.json — what a version file gave at that commit

The keys are the first 16 hex of the SHA-256 of the repository's name and of the
graph file's path, so any name — ``owner/name`` or a local path — is one safe folder,
and two graphs of one repository at one commit stay apart. The ``versions`` folder of
the layout before them is removed on opening. A file is written
to a temporary name and renamed, so a reader never sees half of one. What the host said —
the fetch times, each version's pull request, each tag's release, the pull requests
still open — is kept on disk too, in ``<folder>/host.json``, so a restart reads none
of it again: a repository is fetched, and each of those read, only when it is due.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.version_source import NumberRead

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage

#: The file that keeps what the host said, beside the graphs.
HOST_FILE = "host.json"


@meta(description="A version's graph and facts on disk, by commit; when each repository was fetched", domain=RepoGraphDomain)
class VersionCache(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: Keep what never changes for a commit, and when each repository was last fetched.
    CONTRACT: ``keep`` stores a version's bytes and facts by ``(repository, graph_file, sha)``; ``graph`` and ``facts`` return them, or ``None`` before ``keep``; ``fetched_at`` returns the time ``mark_fetched`` was given, or ``None``; pull requests, releases, open pull requests and fetch times are kept with their read time until forgotten, across restarts.
    INVARIANTS: Kept entries are never changed or removed; a reader never sees a half-written file.
    AI-CORE-END
    """

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        shutil.rmtree(folder / "versions", ignore_errors=True)
        self._fetched: dict[str, float] = {}
        self._pulls: dict[tuple[str, str], tuple[dict[str, str | int] | None, float]] = {}
        self._releases: dict[tuple[str, str], tuple[dict[str, str] | None, float]] = {}
        self._open: dict[tuple[str, str], tuple[list[dict[str, str | int]], float]] = {}
        self._load()

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same cache."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the cache is not a rollup target."""
        return False

    def keep(self, repository: str, graph_file: str, sha: str, content: bytes, facts: GraphFacts) -> None:
        """Store a version's file and its facts for good."""
        place = self._place(repository, graph_file)
        place.mkdir(parents=True, exist_ok=True)
        _write(place / f"{sha}.graph", content)
        _write(place / f"{sha}.json", json.dumps({"nodes": facts.nodes, "edges": facts.edges, "refused": facts.refused}).encode())

    def graph(self, repository: str, graph_file: str, sha: str) -> bytes | None:
        """A kept version's file, or ``None``."""
        try:
            return (self._place(repository, graph_file) / f"{sha}.graph").read_bytes()
        except FileNotFoundError:
            return None

    def facts(self, repository: str, graph_file: str, sha: str) -> GraphFacts | None:
        """A kept version's facts, or ``None``."""
        try:
            kept = json.loads((self._place(repository, graph_file) / f"{sha}.json").read_bytes())
        except FileNotFoundError:
            return None
        return GraphFacts(nodes=kept["nodes"], edges=kept["edges"], refused=kept["refused"])

    def detail(self, repository: str, graph_file: str, sha: str) -> dict[str, object] | None:
        """A kept version's detail — its contribution and graph change — or ``None``."""
        try:
            return dict(json.loads((self._place(repository, graph_file) / f"{sha}.detail.json").read_bytes()))
        except FileNotFoundError:
            return None

    def keep_detail(self, repository: str, graph_file: str, sha: str, detail: dict[str, object]) -> None:
        """Store a version's detail for good: it belongs to the commit and to the version before it on the chain."""
        place = self._place(repository, graph_file)
        place.mkdir(parents=True, exist_ok=True)
        _write(place / f"{sha}.detail.json", json.dumps(detail).encode())

    def number(self, repository: str, file: str, key: str, sha: str) -> NumberRead | None:
        """What a version file gave for ``key`` at ``sha``, or ``None`` before any read."""
        try:
            kept = json.loads((self._numbers(repository, file, key) / f"{sha}.json").read_bytes())
        except FileNotFoundError:
            return None
        return NumberRead(number=kept["number"], reason=kept["reason"])

    def keep_number(self, repository: str, file: str, key: str, sha: str, read: NumberRead) -> None:
        """Store what a version file gave at ``sha`` for good: it belongs to the commit."""
        place = self._numbers(repository, file, key)
        place.mkdir(parents=True, exist_ok=True)
        _write(place / f"{sha}.json", json.dumps({"number": read.number, "reason": read.reason}).encode())

    def pull_request(self, repository: str, sha: str) -> tuple[dict[str, str | int] | None, float] | None:
        """A version's pull request as last read (``None`` when it had none) and when it was read; ``None`` before any read."""
        return self._pulls.get((repository, sha))

    def keep_pull_request(self, repository: str, sha: str, pull: dict[str, str | int] | None, at: float) -> None:
        """Remember a version's pull request, read at ``at``."""
        self._pulls[(repository, sha)] = (pull, at)
        self._save()

    def forget_pull_request(self, repository: str, sha: str) -> None:
        """Drop a version's pull request, so the next read asks the host again."""
        self._pulls.pop((repository, sha), None)
        self._save()

    def release(self, repository: str, tag: str) -> tuple[dict[str, str] | None, float] | None:
        """A tag's release as last read (``None`` when it had none) and when it was read; ``None`` before any read."""
        return self._releases.get((repository, tag))

    def keep_release(self, repository: str, tag: str, release: dict[str, str] | None, at: float) -> None:
        """Remember a tag's release, read at ``at``."""
        self._releases[(repository, tag)] = (release, at)
        self._save()

    def forget_releases(self, repository: str) -> None:
        """Drop every release of ``repository``, so the next read asks the host again."""
        for key in [key for key in self._releases if key[0] == repository]:
            del self._releases[key]
        self._save()

    def open_pull_requests(self, repository: str, branch: str) -> tuple[list[dict[str, str | int]], float] | None:
        """The pull requests open into ``branch`` as the host last told them, and when; ``None`` before any read."""
        return self._open.get((repository, branch))

    def keep_open_pull_requests(self, repository: str, branch: str, pulls: list[dict[str, str | int]], at: float) -> None:
        """Remember the pull requests open into ``branch``, read at ``at``."""
        self._open[(repository, branch)] = (pulls, at)
        self._save()

    def fetched_at(self, repository: str) -> float | None:
        """When ``repository`` was last fetched, as given to ``mark_fetched``, or ``None``."""
        return self._fetched.get(repository)

    def mark_fetched(self, repository: str, at: float) -> None:
        """Remember that ``repository`` was fetched at ``at``."""
        self._fetched[repository] = at
        self._save()

    def _load(self) -> None:
        """Take back what the host said before a restart; a missing or unreadable file starts empty."""
        try:
            kept = json.loads((self._folder / HOST_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self._fetched = {str(name): float(at) for name, at in kept.get("fetched", {}).items()}
        self._pulls = {(row[0], row[1]): (row[2], float(row[3])) for row in kept.get("pulls", [])}
        self._releases = {(row[0], row[1]): (row[2], float(row[3])) for row in kept.get("releases", [])}
        self._open = {(row[0], row[1]): (row[2], float(row[3])) for row in kept.get("open", [])}

    def _save(self) -> None:
        """Write what the host said, whole, so a restart finds it."""
        document = {
            "fetched": self._fetched,
            "pulls": [[repository, sha, pull, at] for (repository, sha), (pull, at) in self._pulls.items()],
            "releases": [[repository, tag, release, at] for (repository, tag), (release, at) in self._releases.items()],
            "open": [[repository, branch, pulls, at] for (repository, branch), (pulls, at) in self._open.items()],
        }
        self._folder.mkdir(parents=True, exist_ok=True)
        _write(self._folder / HOST_FILE, json.dumps(document).encode())

    def _numbers(self, repository: str, file: str, key: str) -> Path:
        """The folder of one version file's numbers under one key."""
        return self._folder / "numbers" / _key(repository) / _key(f"{file}\0{key}")

    def _place(self, repository: str, graph_file: str) -> Path:
        """The folder of one graph file's versions."""
        return self._folder / "graphs" / _key(repository) / _key(graph_file)


def _key(name: str) -> str:
    """A safe folder name for ``name``."""
    return hashlib.sha256(name.encode()).hexdigest()[:16]


def _write(target: Path, content: bytes) -> None:
    """Write ``content`` to a temporary file beside ``target`` and rename it into place."""
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    with os.fdopen(handle, "wb") as out:
        out.write(content)
    os.replace(temporary, target)
