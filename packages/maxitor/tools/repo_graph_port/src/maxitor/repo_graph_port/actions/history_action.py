# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/actions/history_action.py
"""
HistoryAction — a history's versions, oldest first, each with its tags and facts.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The list a reader picks versions from: every first-parent commit that changed the
graph file, its date and message, the repository's tags placed on it, and its
graph's counts or why it is refused. ``after`` returns only the versions newer than
the one a reader already holds.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    history id ──► config ──► mirror refreshed after the fallback interval
               ──► versions + first-parent chain + tags ──► place_tags
               ──► each version's facts and detail — who made it, its size, its graph change — (cache, or git once),
                   its pull request and its tags' releases
                   (cache while fresh, or the host; a pull request else from its merge commit's message)
               ──► [VersionRecord, …], and the open pull requests that change the graph ──► proposals

The adapter tags the answer with an ``ETag`` of its body, so a repeated read of an
unchanged history is answered ``304``.
"""

from __future__ import annotations

import asyncio
from typing import cast

from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_reading import (
    chosen,
    detail_of,
    facts_of,
    proposals_of,
    pull_request_of,
    refreshed,
    release_of,
)
from maxitor.repo_graph_port.history_versions import place_tags, pull_request_in_message
from maxitor.repo_graph_port.placed_tag import PlacedTag
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
from maxitor.repo_graph_port.version_record import VersionRecord
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class HistoryParams(BaseParams):
    """The history to list, and the version a reader already holds."""

    history: str | None = Field(default=None, description="A configured history's id; its read key must open it")
    link: str | None = Field(default=None, description="A link to a public repository's graph file, in place of an id")
    after: str | None = Field(default=None, description="Only the versions newer than this sha")


class HistoryResult(BaseResult):
    """The versions, oldest first."""

    versions: list[VersionRecord] = Field(description="The history's versions, oldest first")
    proposals: list[VersionRecord] = Field(default_factory=list, description="Pull requests still open into the branch that change the graph, each with its state")


@meta(description="List a graph's versions with their tags and facts", domain=RepoGraphDomain)
@check_roles(GuestRole)
@connection(HistoriesConfig, key="HistoriesConfig", description="The histories this server serves")
@connection(GitMirror, key="GitMirror", description="The repositories' history, read with git")
@connection(GitHubHost, key="GitHubHost", description="GitHub: the App's token, pull requests, releases")
@connection(VersionCache, key="VersionCache", description="Each version's facts, read once")
class HistoryAction(BaseAction[HistoryParams, HistoryResult]):
    """
    AI-CORE-BEGIN
    ROLE: List a history's versions for a reader to choose from.
    CONTRACT: Oldest first; ``after`` drops it and every older version; a history the request may not open, or an ``after`` that is not a version, raises ``HistoryNotFoundError``.
    INVARIANTS: Reads only; each version's file is read from git once, then from the cache.
    AI-CORE-END
    """

    @summary_aspect("List the history's versions")
    @context_requires("env.history_refresh_seconds", "user.history", "user.user_id")
    async def history_summary(
        self,
        params: HistoryParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> HistoryResult:
        """Refresh the repository, place the tags, gather every version's facts, pull request and releases."""
        mirror = cast(GitMirror, connections["GitMirror"])
        host = cast(GitHubHost, connections["GitHubHost"])
        cache = cast(VersionCache, connections["VersionCache"])
        history = chosen(cast(HistoriesConfig, connections["HistoriesConfig"]), params.history, params.link, ctx.get("user.history"))
        interval = ctx.get("env.history_refresh_seconds")
        await refreshed(mirror, cache, host, history, interval)
        commits = await asyncio.to_thread(mirror.versions, history.repository, history.branch, history.graph_file)
        shas = [commit.sha for commit in commits]
        if params.after is not None and params.after not in shas:
            raise HistoryNotFoundError()
        chain = await asyncio.to_thread(mirror.first_parents, history.repository, history.branch)
        tags = place_tags(chain, shas, await asyncio.to_thread(mirror.tags, history.repository))
        start = shas.index(params.after) + 1 if params.after is not None else 0
        pull_url = f"https://github.com/{history.repository}/pull/" if history.host == "github" else ""
        records: list[VersionRecord] = []
        for index, commit in enumerate(commits[start:], start=start):
            facts = await facts_of(mirror, cache, host, history, commit.sha)
            contribution, change = await detail_of(mirror, cache, host, history, commit.sha, shas[index - 1] if index > 0 else None)
            # The host tells a version's pull request; where it does not (a local repository, or GitHub without
            # an answer), the merge or squash commit's message names it.
            pull = await pull_request_of(cache, host, history, commit.sha, interval) or pull_request_in_message(commit.message, pull_url)
            placed = [PlacedTag(name=name, release=await release_of(cache, host, history, name, interval)) for name in tags.get(commit.sha, [])]
            records.append(VersionRecord(
                sha=commit.sha,
                date=commit.date,
                pr=pull,
                message=None if pull is not None else commit.message,
                tags=placed,
                nodes=facts.nodes,
                edges=facts.edges,
                refused=facts.refused,
                contribution=contribution,
                change=change,
            ))
        proposals = await proposals_of(mirror, cache, host, history, shas[-1] if shas else None, interval)
        await box.info(Channel.business, "History {%var.history} listed for {%var.reader}", history=history.id, reader=ctx.get("user.user_id") or "a guest")
        return HistoryResult(versions=records, proposals=proposals)
