# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/resources/git_mirror.py
"""
GitMirror — a repository's history, read with the ``git`` command.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The versions of a graph are the commits, by first parent, that changed its file;
their bytes, dates and messages, and the repository's tags, are all in git. This
resource reads them: from a local repository as it is, or from a bare partial
mirror of a remote one kept under a cache folder (commits and trees fetched,
file contents only when a version's file is read).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    open(repository[, url]) ──► local path as it is, or git clone --bare --filter=blob:none
    fetch(repository)       ──► git fetch (branches and tags), one at a time per repository
    versions / first_parents / tags / file_at ──► git log / rev-list / for-each-ref / show
    contribution / proposal                   ──► rev-list --parents, log, merge-base, diff --shortstat
    pull_heads / merged / commit              ──► for-each-ref refs/pull, merge-base --is-ancestor, log -1

Every call is ``subprocess.run`` with an argument list, no shell, a timeout and
no terminal prompt. ``auth`` is git configuration for that one call — the host's
credentials as an ``http.<url>.extraheader`` — passed through ``GIT_CONFIG_COUNT`` /
``GIT_CONFIG_KEY_<n>`` / ``GIT_CONFIG_VALUE_<n>`` after any the environment already
holds; it is never stored, logged, put in a remote URL or written to the mirror's config.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from maxitor.repo_graph_port.commit import Commit
from maxitor.repo_graph_port.contribution import Contribution
from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.tag import Tag

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


@meta(description="The history of a repository, read with git from a local path or a partial mirror", domain=RepoGraphDomain)
class GitMirror(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: Read a repository's first-parent history, tags and files with git.
    CONTRACT: ``open`` names a repository — a local path, or ``owner/name`` with the ``url`` to mirror it from; every other method takes that name. Remote mirrors live under ``cache``; ``fetch`` and ``open`` run one at a time per repository.
    INVARIANTS: Never writes a local repository; ``auth`` lives only in the environment of the call it is given to.
    AI-CORE-END
    """

    def __init__(self, cache: Path) -> None:
        self._cache = cache
        self._places: dict[str, Path] = {}
        self._remote: set[str] = set()
        self._locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same mirror."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the mirror is not a rollup target."""
        return False

    def open(self, repository: str, url: str | None = None, auth: Mapping[str, str] | None = None) -> None:
        """Make ``repository`` readable: a local path as it is, or a bare partial mirror of ``url`` under the cache."""
        if url is None:
            place = Path(repository)
            self._git(place, ["rev-parse", "--git-dir"])
            self._places[repository] = place
            return
        if re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repository) is None or ".." in repository:
            raise ValueError(f"a mirrored repository is named owner/name, got {repository!r}")
        place = self._cache / "mirrors" / f"{repository.replace('/', '__')}.git"
        with self._lock(repository):
            if not place.is_dir():
                place.parent.mkdir(parents=True, exist_ok=True)
                # Cloned beside its place and renamed only when complete: a clone that fails or times out
                # never leaves a half-made mirror that a later start would take for a whole one.
                partial = place.with_name(place.name + ".partial")
                shutil.rmtree(partial, ignore_errors=True)
                try:
                    self._git(None, ["clone", "--bare", "--filter=blob:none", "--", url, str(partial)], auth)
                except GitError:
                    shutil.rmtree(partial, ignore_errors=True)
                    raise
                partial.rename(place)
            self._places[repository] = place
            self._remote.add(repository)

    def is_open(self, repository: str) -> bool:
        """Whether ``open`` was called for ``repository`` in this process."""
        return repository in self._places

    def fetch(self, repository: str, auth: Mapping[str, str] | None = None) -> None:
        """Bring a mirror's branches and tags up to date; a local repository is always current."""
        if repository not in self._remote:
            self._place(repository)
            return
        with self._lock(repository):
            # Open pull requests are read from the heads GitHub keeps for them.
            refspecs = ["+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/pull/*/head:refs/pull/*/head"]
            self._git(self._place(repository), ["fetch", "--prune", "--filter=blob:none", "origin", *refspecs], auth)

    def versions(self, repository: str, branch: str, path: str) -> list[Commit]:
        """The commits of ``branch``, by first parent, that changed ``path`` — oldest first."""
        out = self._git(
            self._place(repository),
            ["log", "--first-parent", "--reverse", "--format=%H%x1f%cI%x1f%B%x1e", branch, "--", path],
        )
        commits: list[Commit] = []
        for record in out.decode("utf-8").split("\x1e"):
            record = record.lstrip("\n")
            if not record:
                continue
            sha, date, message = record.split("\x1f", 2)
            utc = datetime.fromisoformat(date).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            commits.append(Commit(sha=sha, date=utc, message=message.rstrip("\n")))
        return commits

    def first_parents(self, repository: str, branch: str) -> list[str]:
        """Every commit of ``branch`` by first parent, oldest first — the chain a tag must sit on to be placed."""
        out = self._git(self._place(repository), ["rev-list", "--first-parent", "--reverse", branch])
        return out.decode("ascii").split()

    def tags(self, repository: str) -> list[Tag]:
        """The repository's tags, each with the commit it marks (an annotated tag followed to its commit)."""
        out = self._git(
            self._place(repository),
            ["for-each-ref", "refs/tags", "--format=%(refname:short)%1f%(objectname)%1f%(*objectname)"],
        )
        found: list[Tag] = []
        for line in out.decode("utf-8").splitlines():
            name, target, peeled = line.split("\x1f")
            found.append(Tag(name=name, sha=peeled or target))
        return found

    def changed(self, repository: str, before: str, after: str, path: str) -> bool:
        """Whether ``path`` changed by first parent between ``before`` and ``after``; a history git cannot compare that way counts as changed."""
        if set(before) == {"0"}:
            return True
        try:
            out = self._git(self._place(repository), ["log", "--first-parent", "--format=%H", f"{before}..{after}", "--", path])
        except GitError:
            # ``before`` is gone — a forced push: the history is read again whole.
            return True
        return bool(out.strip())

    def file_at(self, repository: str, sha: str, path: str, auth: Mapping[str, str] | None = None) -> bytes | None:
        """The bytes of ``path`` at commit ``sha`` exactly as committed, or ``None`` when the commit has no such file."""
        place = self._place(repository)
        if not self._git(place, ["ls-tree", "--name-only", sha, "--", path], auth).strip():
            return None
        return self._git(place, ["show", f"{sha}:{path}"], auth)

    def pull_heads(self, repository: str) -> dict[int, str]:
        """Every pull request head the repository keeps (``refs/pull/<n>/head``), by number."""
        out = self._git(self._place(repository), ["for-each-ref", "refs/pull", "--format=%(refname)%1f%(objectname)"])
        heads: dict[int, str] = {}
        for line in out.decode("utf-8").splitlines():
            name, sha = line.split("\x1f")
            parts = name.split("/")
            if len(parts) == 4 and parts[3] == "head" and parts[2].isdigit():
                heads[int(parts[2])] = sha
        return heads

    def merged(self, repository: str, sha: str, branch: str) -> bool:
        """Whether ``sha`` is already in ``branch``."""
        try:
            self._git(self._place(repository), ["merge-base", "--is-ancestor", sha, branch])
        except GitError:
            return False
        return True

    def commit(self, repository: str, sha: str) -> Commit:
        """One commit: its date in UTC and its whole message."""
        out = self._git(self._place(repository), ["log", "-1", "--format=%cI%x1f%B", sha]).decode("utf-8")
        date, message = out.split("\x1f", 1)
        utc = datetime.fromisoformat(date.strip()).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return Commit(sha=sha, date=utc, message=message.rstrip("\n"))

    def proposal(self, repository: str, branch: str, head: str, auth: Mapping[str, str] | None = None) -> Contribution:
        """Who made an open pull request and how large it is: the authors of its commits not yet in ``branch``, its diff against where it left ``branch``."""
        place = self._place(repository)
        names = [name for name in self._git(place, ["log", "--reverse", "--format=%an", f"{branch}..{head}"]).decode("utf-8").split("\n") if name]
        base = self._git(place, ["merge-base", branch, head]).decode("ascii").strip()
        stat = self._git(place, ["diff", "--shortstat", base, head], auth).decode("utf-8")
        author = names[0] if names else self._git(place, ["log", "-1", "--format=%an", head]).decode("utf-8").strip()
        return Contribution(author=author, co_authors=max(len(set(names)) - 1, 0), merged_by=None, **_shortstat(stat))

    def contribution(self, repository: str, sha: str, auth: Mapping[str, str] | None = None) -> Contribution:
        """Who made the version ``sha`` and how large it was: a merge commit's branch authors and merger, or a commit's author; its diff against its first parent."""
        place = self._place(repository)
        parents = self._git(place, ["rev-list", "--parents", "-n", "1", sha]).decode("ascii").split()[1:]
        own = self._git(place, ["log", "-1", "--format=%an", sha]).decode("utf-8").strip()
        author, co_authors, merged_by = own, 0, None
        if len(parents) > 1:
            branch = self._git(place, ["log", "--reverse", "--format=%an", f"{parents[0]}..{parents[1]}"]).decode("utf-8").split("\n")
            names = [name for name in branch if name]
            if names:
                author, co_authors, merged_by = names[0], len(set(names)) - 1, own
        # A first commit has no parent to compare with: its whole content is the change.
        arguments = ["diff", "--shortstat", parents[0], sha] if parents else ["show", "--shortstat", "--format=", sha]
        stat = self._git(place, arguments, auth).decode("utf-8")
        return Contribution(author=author, co_authors=co_authors, merged_by=merged_by, **_shortstat(stat))

    def _place(self, repository: str) -> Path:
        """Where git reads ``repository``; it must have been opened."""
        try:
            return self._places[repository]
        except KeyError:
            raise KeyError(f"repository {repository!r} was not opened") from None

    def _lock(self, repository: str) -> threading.Lock:
        """The lock that keeps one clone or fetch of ``repository`` at a time."""
        with self._locks_lock:
            return self._locks.setdefault(repository, threading.Lock())

    def _git(self, place: Path | None, arguments: list[str], auth: Mapping[str, str] | None = None) -> bytes:
        """Run one git command in ``place`` and return its standard output; a failure or a timeout is a ``GitError``."""
        timeout_seconds = 300
        command = ["git", *(["-C", str(place)] if place is not None else []), *arguments]
        environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        held = int(environment.get("GIT_CONFIG_COUNT", "0"))
        for index, (key, value) in enumerate((auth or {}).items(), start=held):
            environment[f"GIT_CONFIG_KEY_{index}"] = key
            environment[f"GIT_CONFIG_VALUE_{index}"] = value
        environment["GIT_CONFIG_COUNT"] = str(held + len(auth or {}))
        try:
            done = subprocess.run(command, capture_output=True, env=environment, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired:
            raise GitError(arguments[0], f"no answer in {timeout_seconds} s") from None
        if done.returncode != 0:
            raise GitError(arguments[0], done.stderr.decode("utf-8", "replace").strip())
        return done.stdout


def _shortstat(line: str) -> dict[str, int]:
    """``N files changed, A insertions(+), D deletions(-)`` read into files, additions and deletions; a part git leaves out is 0."""
    found = {"files": r"(\d+) files? changed", "additions": r"(\d+) insertions?\(\+\)", "deletions": r"(\d+) deletions?\(-\)"}
    return {key: int(match.group(1)) if (match := re.search(pattern, line)) else 0 for key, pattern in found.items()}
