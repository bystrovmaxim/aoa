# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/history_reading.py
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

    found(config, id)                    ──► History, or HistoryNotFoundError
    refreshed(mirror, cache, history, s) ──► mirror opened; fetched when older than s seconds
    facts_of / graph_of(..., sha)        ──► the cache, or git once and then the cache

git is blocking, so every mirror call runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import time

from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.history import History
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_versions import graph_facts
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache


def found(config: HistoriesConfig, history_id: str) -> History:
    """The configured history ``history_id``; any other id is "not found"."""
    history = config.history(history_id)
    if history is None:
        raise HistoryNotFoundError()
    return history


async def refreshed(mirror: GitMirror, cache: VersionCache, history: History, interval_seconds: int) -> None:
    """Open the history's repository, and fetch it when its last fetch is older than ``interval_seconds``."""
    if history.host != "local":
        # Reading a hosted repository comes with its host resource; until then it is not served.
        raise HistoryNotFoundError()
    if not mirror.is_open(history.repository):
        await asyncio.to_thread(mirror.open, history.repository)
    last = cache.fetched_at(history.repository)
    now = time.time()
    if last is None or now - last >= interval_seconds:
        await asyncio.to_thread(mirror.fetch, history.repository)
        cache.mark_fetched(history.repository, now)


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
