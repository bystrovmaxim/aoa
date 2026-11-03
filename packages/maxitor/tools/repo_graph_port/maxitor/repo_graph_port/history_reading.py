# packages/maxitor/tools/repo_graph_port/maxitor/repo_graph_port/history_reading.py
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
    detail_of(..., sha, before)                 ──► who made it, its size, its graph change: the cache, or git once
    pull_request_of / release_of(..., s)        ──► the cache while younger than s seconds, or the host
    proposals_of(..., newest, s, number)        ──► the open pull requests that change the graph or the version, as versions to look at

git is blocking, so every mirror call runs in a worker thread. A local history has
no host: no pull requests, no releases. When GitHub does not answer, a version shows
its commit's message and a tag no release — what was read before, if anything — and
nothing is kept, so the next read asks again.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import PurePosixPath
from typing import cast

import httpx
from maxitor.repo_graph_port.contribution import Contribution
from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.history import History, public_history
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_point import HistoryPoint
from maxitor.repo_graph_port.history_versions import graph_change, graph_differs, graph_facts
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
from maxitor.repo_graph_port.version_record import VersionRecord
from maxitor.repo_graph_port.version_source import (
    BROKEN,
    DRIVER,
    FORMAT,
    MISSING,
    NOT_A_STRING,
    NumberRead,
    read_number,
)

_REASONS = {
    MISSING: "{file} has no {key}",
    NOT_A_STRING: "{key} in {file} is not a written number; a computed or inherited version cannot be read",
    BROKEN: "{file} cannot be read",
    FORMAT: "{file} is neither TOML nor JSON; link a component's version.toml, or use no version file",
    DRIVER: "{file} names a driver and holds no number; link the file the driver reads, with its key",
}


def chosen(
    config: HistoriesConfig,
    history_id: str | None,
    link: str | None,
    reader_history: str | None,
    version_link: str | None = None,
    version_key: str | None = None,
) -> History:
    """
    The history a request names: a configured one by id, which the reader's key must open, or a public one by link.

    Exactly one of ``history_id`` and ``link`` names it; anything else — both, neither, an unknown id, a key that
    opens another history or none, a link that is not a public graph file's — is "not found".
    """
    if link is not None and history_id is None:
        history = public_history(link, version_link, version_key)
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
    kept = cache.facts(history.repository, history.graph_file, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, host, history, sha))[1]


async def graph_of(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str) -> bytes:
    """A version's file: kept, or read from git once and kept."""
    kept = cache.graph(history.repository, history.graph_file, sha)
    if kept is not None:
        return kept
    return (await _read(mirror, cache, host, history, sha))[0]


async def detail_of(
    mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str, before: str | None, touched: bool = True
) -> tuple[Contribution, dict[str, object]]:
    """A version's contribution and what it did to the graph of ``before``: kept, or read once and kept; a commit that did not touch the graph reads none."""
    kept = cache.detail(history.repository, history.graph_file, sha)
    if kept is not None:
        return Contribution.model_validate(kept["contribution"]), cast(dict[str, object], kept["change"])
    auth = await credentials(host, history)
    contribution = await asyncio.to_thread(mirror.contribution, history.repository, sha, auth)
    if touched:
        previous = await graph_of(mirror, cache, host, history, before) if before is not None else None
        change = graph_change(previous, await graph_of(mirror, cache, host, history, sha))
    else:
        change = graph_change(b"", b"")
    cache.keep_detail(history.repository, history.graph_file, sha, {"contribution": contribution.model_dump(), "change": change})
    return contribution, change


async def pull_request_of(cache: VersionCache, host: GitHubHost, history: History, sha: str, interval_seconds: int) -> dict[str, str | int] | None:
    """A version's pull request: one found is kept until a webhook forgets it; none found is asked again after ``interval_seconds``."""
    if history.host != "github":
        return None
    kept = cache.pull_request(history.repository, sha)
    now = time.time()
    if kept is not None and (kept[0] is not None or now - kept[1] < interval_seconds):
        return kept[0]
    try:
        pull = await host.pull_request_of(history.repository, sha, await _token(host, history))
    except httpx.HTTPError:
        # GitHub did not answer (down, or out of its rate limit): the version shows its message; the next read asks again.
        return kept[0] if kept is not None else None
    cache.keep_pull_request(history.repository, sha, pull, now)
    return pull


async def release_of(cache: VersionCache, host: GitHubHost, history: History, tag: str, interval_seconds: int) -> dict[str, str] | None:
    """A tag's release: one found is kept until a webhook forgets it; none found is asked again after ``interval_seconds``."""
    if history.host != "github":
        return None
    kept = cache.release(history.repository, tag)
    now = time.time()
    if kept is not None and (kept[0] is not None or now - kept[1] < interval_seconds):
        return kept[0]
    try:
        release = await host.release_of(history.repository, tag, await _token(host, history))
    except httpx.HTTPError:
        # GitHub did not answer: the tag shows no release this time; the next read asks again.
        return kept[0] if kept is not None else None
    cache.keep_release(history.repository, tag, release, now)
    return release


async def _token(host: GitHubHost, history: History) -> str | None:
    """The App's token for a private history; for a public one, any installation's token, or none — anonymous — without an App."""
    if not history.public:
        return await host.token_for(history.repository)
    try:
        return await host.public_token()
    except httpx.HTTPError:
        # The App could not give a token: read anonymously, within the anonymous limit.
        return None


async def _read(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str) -> tuple[bytes, GraphFacts]:
    """Read a version's file from git, decide its facts, keep both."""
    auth = await credentials(host, history)
    found = await asyncio.to_thread(mirror.first_file_at, history.repository, sha, history.graph_paths, auth)
    if found is None:
        content, facts = b"", GraphFacts(nodes=None, edges=None, refused="the commit removed the graph file")
    else:
        content, facts = found[1], graph_facts(found[1])
    cache.keep(history.repository, history.graph_file, sha, content, facts)
    return content, facts


async def number_at(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, file: str, sha: str) -> NumberRead:
    """What the version file gives at ``sha``: kept, or read once and kept."""
    kept = cache.number(history.repository, file, history.version_key, sha)
    if kept is not None:
        return kept
    auth = await credentials(host, history)
    found = await asyncio.to_thread(mirror.first_file_at, history.repository, sha, history.version_paths, auth)
    read = read_number(found[0], found[1], history.version_key) if found is not None else NumberRead(reason=MISSING)
    cache.keep_number(history.repository, file, history.version_key, sha, read)
    return read


async def points_of(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History) -> list[HistoryPoint]:
    """
    AI-CORE-BEGIN
    ROLE: Join a history's graph file and version file into its points, oldest first.
    CONTRACT: With no version file, every commit that changed the graph file is a point, as it always was. With one, a commit that changed either file is a point only if the graph document or the readable number changed; the list starts at the first commit of the graph file.
    INVARIANTS: A commit that did not touch the graph reads no graph.
    AI-CORE-END
    """
    graph_commits = await asyncio.to_thread(mirror.versions, history.repository, history.branch, *history.graph_paths)
    file = history.version_file
    if file is None:
        shas = [commit.sha for commit in graph_commits]
        return [HistoryPoint(commit, commit.sha, shas[index - 1] if index else None) for index, commit in enumerate(graph_commits)]
    if not graph_commits:
        return []
    watched = await asyncio.to_thread(mirror.versions, history.repository, history.branch, *history.watched_paths)
    touched = {commit.sha for commit in graph_commits}
    start = next(index for index, commit in enumerate(watched) if commit.sha == graph_commits[0].sha)
    points: list[HistoryPoint] = []
    graph_at = graph_commits[0].sha
    before: str | None = None
    number: str | None = None
    for commit in watched[start:]:
        graph_changed = False
        previous = before
        if commit.sha in touched:
            graph_changed = await _graph_moved(mirror, cache, host, history, commit.sha, before)
            graph_at = before = commit.sha
        read = await number_at(mirror, cache, host, history, file, commit.sha)
        version_changed = read.number is not None and read.number != number
        number = read.number or number
        if graph_changed or version_changed:
            points.append(HistoryPoint(commit, graph_at, previous if commit.sha in touched else None, graph_changed, read.number, version_changed))
    return points


async def _graph_moved(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, sha: str, before: str | None) -> bool:
    """Whether the commit changed the graph document of ``before``, the last commit that touched it."""
    _, change = await detail_of(mirror, cache, host, history, sha, before)
    previous = await graph_of(mirror, cache, host, history, before) if before is not None else None
    return graph_differs(previous, await graph_of(mirror, cache, host, history, sha), change)


async def version_problem_of(mirror: GitMirror, host: GitHubHost, history: History) -> str | None:
    """
    AI-CORE-BEGIN
    ROLE: Say in plain words why a history's version cannot be read at the head of its branch.
    CONTRACT: ``None`` with no version file, and when the number reads. Never raises for a bad link, and never stops the history.
    AI-CORE-END
    """
    if history.version_refused is not None:
        return history.version_refused
    if history.version_file is None:
        return None
    file = history.version_file
    folder = PurePosixPath(file).parent
    if folder != PurePosixPath(".") and folder not in PurePosixPath(history.graph_file).parents:
        return f"{file} is not in a folder above {history.graph_file}"
    chain = await asyncio.to_thread(mirror.first_parents, history.repository, history.branch)
    auth = await credentials(host, history)
    if await asyncio.to_thread(mirror.file_at, history.repository, chain[-1], history.graph_file, auth) is None:
        return f"{history.graph_file} is not on {history.branch}"
    content = await asyncio.to_thread(mirror.file_at, history.repository, chain[-1], file, auth)
    if content is None:
        return f"{file} is not on {history.branch}"
    read = read_number(file, content, history.version_key)
    return None if read.reason is None else _REASONS[read.reason].format(file=file, key=history.version_key)


async def proposals_of(
    mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, newest: str | None, interval_seconds: int, newest_number: str | None = None
) -> list[VersionRecord]:
    """
    AI-CORE-BEGIN
    ROLE: List the pull requests still open into the history's branch that change its graph or its version, for a reader to look at before they are merged.
    CONTRACT: On GitHub, the host's open pull requests offered for review, drafts left out, with their state — changes_requested, approved or open — kept while younger than ``interval_seconds``; in a local repository, every ``refs/pull/<n>/head`` not yet in the branch, state ``open``, its title the head commit's first line. Only those whose graph differs from ``newest``'s, or, in a history with a version file, whose readable number differs from ``newest_number``, the newest point's, are listed — the second kind with ``graph_changed`` false —, oldest number first, each with its facts, its authors and size against where it left the branch, and its change against ``newest``. Never raises for a host that does not answer: it lists what it last knew.
    AI-CORE-END
    """
    pulls = await _open_pulls(mirror, cache, host, history, interval_seconds)
    before = await graph_of(mirror, cache, host, history, newest) if newest is not None else None
    auth = await credentials(host, history)
    found: list[VersionRecord] = []
    for pull in sorted(pulls, key=lambda each: int(each["number"])):
        try:
            record = await _proposal(mirror, cache, host, history, pull, before, newest_number, auth)
        except GitError:
            # GitHub listed a head the mirror does not have yet: the next fetch brings it.
            continue
        if record is not None:
            found.append(record)
    return found


async def _open_pulls(mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, interval_seconds: int) -> list[dict[str, str | int]]:
    """The pull requests open into the history's branch: the host's, kept a while, or a local repository's pull heads."""
    if history.host == "github":
        kept = cache.open_pull_requests(history.repository, history.branch)
        now = time.time()
        if kept is not None and now - kept[1] < interval_seconds:
            return kept[0]
        try:
            pulls = await host.open_pull_requests(history.repository, history.branch, await _token(host, history))
        except httpx.HTTPError:
            return kept[0] if kept is not None else []
        cache.keep_open_pull_requests(history.repository, history.branch, pulls, now)
        return pulls
    heads = await asyncio.to_thread(mirror.pull_heads, history.repository)
    local: list[dict[str, str | int]] = []
    for number, head in sorted(heads.items()):
        if await asyncio.to_thread(mirror.merged, history.repository, head, history.branch):
            continue
        message = (await asyncio.to_thread(mirror.commit, history.repository, head)).message
        title, _, body = message.partition("\n")
        local.append({"number": number, "title": title.strip(), "body": body.strip("\n"), "url": "", "author": "", "avatar": "", "head": head, "state": "open"})
    return local


async def _proposal(
    mirror: GitMirror, cache: VersionCache, host: GitHubHost, history: History, pull: dict[str, str | int], before: bytes | None, newest_number: str | None, auth: dict[str, str]
) -> VersionRecord | None:
    """One open pull request as a version to look at, or ``None`` when it changes neither the graph nor the version."""
    head = str(pull["head"])
    facts = await facts_of(mirror, cache, host, history, head)
    change = graph_change(before, await graph_of(mirror, cache, host, history, head))
    links = cast(dict[str, int], change["links"])
    graph_changed = bool(change["added"] or change["removed"] or change["changed"] or links["added"] or links["removed"])
    read = await number_at(mirror, cache, host, history, history.version_file, head) if history.version_file is not None else None
    version_changed = read is not None and read.number is not None and read.number != newest_number
    if not graph_changed and not version_changed:
        return None
    commit = await asyncio.to_thread(mirror.commit, history.repository, head)
    contribution = await asyncio.to_thread(mirror.proposal, history.repository, history.branch, head, auth)
    return VersionRecord(
        sha=head,
        date=commit.date,
        pr={key: value for key, value in pull.items() if key != "head"},
        tags=[],
        nodes=facts.nodes,
        edges=facts.edges,
        refused=facts.refused,
        contribution=contribution,
        graph_changed=graph_changed,
        version=read.number if read is not None else None,
        version_changed=version_changed,
        change=change,
    )
