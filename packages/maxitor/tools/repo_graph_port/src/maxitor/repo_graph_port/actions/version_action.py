# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/actions/version_action.py
"""
VersionAction — one version's graph file, exactly as it was committed.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reader compares versions by their graphs, so it needs a version's file. A
version never changes, so its file is read from git once and from the cache ever
after; a ``sha`` that is not a version of the history is "not found".

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    history id + sha ──► config ──► kept in the cache? ──yes──► the file
                                         └─no──► a version of the history? ──► git once ──► kept ──► the file
"""

from __future__ import annotations

import asyncio
from typing import cast

from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_reading import chosen, graph_of, refreshed
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
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


class VersionParams(BaseParams):
    """The version to read."""

    sha: str = Field(description="The version's commit")
    history: str | None = Field(default=None, description="A configured history's id; its read key must open it")
    link: str | None = Field(default=None, description="A link to a public repository's graph file, in place of an id")


class VersionResult(BaseResult):
    """The version's graph file."""

    graph: str = Field(description="The graph file's text, exactly as committed")


@meta(description="Read one version's graph file", domain=RepoGraphDomain)
@check_roles(GuestRole)
@connection(HistoriesConfig, key="HistoriesConfig", description="The histories this server serves")
@connection(GitMirror, key="GitMirror", description="The repositories' history, read with git")
@connection(GitHubHost, key="GitHubHost", description="GitHub: the App's token, pull requests, releases")
@connection(VersionCache, key="VersionCache", description="Each version's file, read once")
class VersionAction(BaseAction[VersionParams, VersionResult]):
    """
    AI-CORE-BEGIN
    ROLE: Give a reader one version's graph file.
    CONTRACT: The file's text as committed; a history the request may not open, or a ``sha`` that is neither one of its versions nor the head of a pull request the repository keeps, raises ``HistoryNotFoundError``.
    INVARIANTS: Reads only; a version kept in the cache is answered without git.
    AI-CORE-END
    """

    @summary_aspect("Read the version's graph file")
    @context_requires("env.history_refresh_seconds", "user.history", "user.user_id")
    async def version_summary(
        self,
        params: VersionParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> VersionResult:
        """Answer from the cache, or check the sha is a version and read it once."""
        mirror = cast(GitMirror, connections["GitMirror"])
        host = cast(GitHubHost, connections["GitHubHost"])
        cache = cast(VersionCache, connections["VersionCache"])
        history = chosen(cast(HistoriesConfig, connections["HistoriesConfig"]), params.history, params.link, ctx.get("user.history"))
        kept = cache.graph(history.repository, params.sha)
        if kept is None:
            await refreshed(mirror, cache, host, history, ctx.get("env.history_refresh_seconds"))
            commits = await asyncio.to_thread(mirror.versions, history.repository, history.branch, history.graph_file)
            # A version, or the head of a pull request still open: a reader looks at it before it is merged.
            heads = await asyncio.to_thread(mirror.pull_heads, history.repository)
            if params.sha not in {commit.sha for commit in commits} and params.sha not in heads.values():
                raise HistoryNotFoundError()
            kept = await graph_of(mirror, cache, host, history, params.sha)
        await box.info(Channel.business, "History {%var.history} version read for {%var.reader}", history=history.id, reader=ctx.get("user.user_id") or "a guest")
        return VersionResult(graph=kept.decode("utf-8"))
