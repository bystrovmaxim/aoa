# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_reading.py
"""
The steps every history action takes: find the history, open and refresh its repository, read a version once, ask the host.

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

    chosen(config, id, link, reader)            ──► History, or HistoryNotFoundError
    credentials(host, history)                  ──► the App's git configuration for a private history, none otherwise
    refreshed(mirror, cache, host, history, s)  ──► mirror opened; fetched when older than s seconds
    facts_of / graph_of(..., sha)               ──► the cache, or git once and then the cache
    pull_request_of / release_of(..., s)        ──► the cache while younger than s seconds, or the host

git is blocking, so every mirror call runs in a worker thread. A local history has
no host: no pull requests, no releases. When GitHub does not answer, a version shows
its commit's message and a tag no release — what was read before, if anything — and
nothing is kept, so the next read asks again.
"""

from __future__ import annotations

import asyncio
import time

import httpx
from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.history import History, public_history
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_versions import graph_facts
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
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


async def credentials(host: GitHubHost, history: History) -> dict[str, str]:
    """git configuration that reads the history's repository: the App's token for a private GitHub one, nothing otherwise."""
    if history.host != "github" or history.public:
        return {}
    token = await host.token_for(history.repository)
    if token is None:
        # Without an App the port cannot read a private repository.
        raise HistoryNotFoundError()
    return GitHubHost.git_auth(token)


async def refreshed(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, interval_seconds: int) -> None:
    """Open the history's repository, and fetch it when its last fetch is older than ``interval_seconds``."""
    auth = await credentials(host, history)
    if not mirror.is_open(history.repository):
        await _open(mirror, history, auth)
    last = cache.fetched_at(history.repository)
    now = time.time()
    if last is None or now - last >= interval_seconds:
        await asyncio.to_thread(mirror.fetch, history.repository, auth)
        cache.mark_fetched(history.repository, now)


async def _open(mirror: GitMirror, history: History, auth: dict[str, str]) -> None:
    """Open the history's repository: a local path as it is, a GitHub one from its address."""
    if history.host == "local":
        await asyncio.to_thread(mirror.open, history.repository)
        return
    try:
        await asyncio.to_thread(mirror.open, history.repository, f"https://github.com/{history.repository}.git", auth)
    except GitError:
        if not history.public:
            raise
        # No such repository, or it is not public: the link names nothing the port can read.
        raise HistoryNotFoundError() from None


async def facts_of(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str) -> GraphFacts:
    """A version's facts: kept, or read from git once and kept."""
    kept = cache.facts(history.repository, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, host, history, sha))[1]


async def graph_of(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str) -> bytes:
    """A version's file: kept, or read from git once and kept."""
    kept = cache.graph(history.repository, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, host, history, sha))[0]


async def pull_request_of(cache: VersionCache, host: GitHubHost, history: History, sha: str, interval_seconds: int) -> dict[str, str | int] | None:
    """A version's pull request: kept while younger than ``interval_seconds`` and not forgotten, or asked of the host."""
    if history.host != "github":
        return None
    kept = cache.pull_request(history.repository, sha)
    now = time.time()
    if kept is not None and now - kept[1] < interval_seconds:
        return kept[0]
    try:
        pull = await host.pull_request_of(history.repository, sha, await _token(host, history))
    except httpx.HTTPError:
        # GitHub did not answer (down, or out of its rate limit): the version shows its message; the next read asks again.
        return kept[0] if kept is not None else None
    cache.keep_pull_request(history.repository, sha, pull, now)
    return pull


async def release_of(cache: VersionCache, host: GitHubHost, history: History, tag: str, interval_seconds: int) -> dict[str, str] | None:
    """A tag's release: kept while younger than ``interval_seconds`` and not forgotten, or asked of the host."""
    if history.host != "github":
        return None
    kept = cache.release(history.repository, tag)
    now = time.time()
    if kept is not None and now - kept[1] < interval_seconds:
        return kept[0]
    try:
        release = await host.release_of(history.repository, tag, await _token(host, history))
    except httpx.HTTPError:
        # GitHub did not answer: the tag shows no release this time; the next read asks again.
        return kept[0] if kept is not None else None
    cache.keep_release(history.repository, tag, release, now)
    return release


async def _token(host: GitHubHost, history: History) -> str | None:
    """The App's token for a private history; none for a public one."""
    return None if history.public else await host.token_for(history.repository)


async def _read(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str) -> tuple[bytes, GraphFacts]:
    """Read a version's file from git, decide its facts, keep both."""
    auth = await credentials(host, history)
    content = await asyncio.to_thread(mirror.file_at, history.repository, sha, history.graph_file, auth)
    if content is None:
        content, facts = b"", GraphFacts(nodes=None, edges=None, refused="the commit removed the graph file")
    else:
        facts = graph_facts(content)
    cache.keep(history.repository, sha, content, facts)
    return content, facts
