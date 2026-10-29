# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_reading.py
"""
The steps every history action takes: find the history, open and refresh its repository, read a version once.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``describe``, ``history`` and ``version`` read the same things the same way. These
functions are those shared steps, called from the actions' aspects with the
resources the actions were given; they hold no state of their own.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    chosen(config, id, link, reader)      ──► History, or HistoryNotFoundError
    refreshed(mirror, cache, history, s) ──► mirror opened; fetched when older than s seconds
    facts_of / graph_of(..., sha)        ──► the cache, or git once and then the cache

git is blocking, so every mirror call runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import time

from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.history import History, public_history
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_versions import graph_facts
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache


def chosen(config: HistoriesConfig, history_id: str | None, link: str | None, reader_history: str | None) -> History:
    """
    The history a request names: a configured one by id, which the reader's key must open, or a public one by link.

    Exactly one of ``history_id`` and ``link`` names it; anything else — both, neither, an unknown id, a key that
    opens another history or none, a link that is not a public graph file's — is "not found".
    """
    if link is not None and history_id is None:
        history = public_history(link)
    elif history_id is not None and link is None and history_id == reader_history:
        history = config.history(history_id)
    else:
        history = None
    if history is None:
        raise HistoryNotFoundError()
    return history


async def refreshed(mirror: GitMirror, cache: VersionCache, history: History, interval_seconds: int) -> None:
    """Open the history's repository, and fetch it when its last fetch is older than ``interval_seconds``."""
    if not mirror.is_open(history.repository):
        await _open(mirror, history)
    last = cache.fetched_at(history.repository)
    now = time.time()
    if last is None or now - last >= interval_seconds:
        await asyncio.to_thread(mirror.fetch, history.repository)
        cache.mark_fetched(history.repository, now)


async def _open(mirror: GitMirror, history: History) -> None:
    """Open the history's repository: a local path as it is, a public GitHub repository anonymously."""
    if history.host == "local":
        await asyncio.to_thread(mirror.open, history.repository)
        return
    if not history.public:
        # A private repository is read with the host's credentials, which come with the host resource.
        raise HistoryNotFoundError()
    try:
        await asyncio.to_thread(mirror.open, history.repository, f"https://github.com/{history.repository}.git")
    except GitError:
        # No such repository, or it is not public: the link names nothing the port can read.
        raise HistoryNotFoundError() from None


async def facts_of(mirror: GitMirror, cache: VersionCache, history: History, sha: str) -> GraphFacts:
    """A version's facts: kept, or read from git once and kept."""
    kept = cache.facts(history.repository, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, history, sha))[1]


async def graph_of(mirror: GitMirror, cache: VersionCache, history: History, sha: str) -> bytes:
    """A version's file: kept, or read from git once and kept."""
    kept = cache.graph(history.repository, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, history, sha))[0]


async def _read(mirror: GitMirror, cache: VersionCache, history: History, sha: str) -> tuple[bytes, GraphFacts]:
    """Read a version's file from git, decide its facts, keep both."""
    content = await asyncio.to_thread(mirror.file_at, history.repository, sha, history.graph_file)
    if content is None:
        content, facts = b"", GraphFacts(nodes=None, edges=None, refused="the commit removed the graph file")
    else:
        facts = graph_facts(content)
    cache.keep(history.repository, sha, content, facts)
    return content, facts
