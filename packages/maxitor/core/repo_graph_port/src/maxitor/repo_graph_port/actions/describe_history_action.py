# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/actions/describe_history_action.py
"""
DescribeHistoryAction — what a history is: where its file lives, how many versions, the newest.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reader opening a history first learns what it opened: the repository, the
branch, the graph file, how many versions there are and which is the newest.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    history id ──► config ──► mirror refreshed ──► versions ──► {id, repository, branch, graph_file, versions, newest}
"""

from __future__ import annotations

import asyncio
from typing import cast

from maxitor.repo_graph_port.history_reading import found, refreshed
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
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
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class DescribeHistoryParams(BaseParams):
    """The history to describe."""

    history: str = Field(description="The history's id in the histories config")


class DescribeHistoryResult(BaseResult):
    """What the history is."""

    id: str = Field(description="The history's id")
    repository: str = Field(description="owner/name on the host, or a local path")
    branch: str = Field(description="The branch whose first parents are the versions")
    graph_file: str = Field(description="The graph file's path in the repository")
    versions: int = Field(description="How many versions the history has")
    newest: str | None = Field(default=None, description="The newest version's sha; none when there is no version")


@meta(description="Describe a graph's history: its repository, branch, file and versions", domain=RepoGraphDomain)
@check_roles(GuestRole)
@connection(HistoriesConfig, key="HistoriesConfig", description="The histories this server serves")
@connection(GitMirror, key="GitMirror", description="The repositories' history, read with git")
@connection(VersionCache, key="VersionCache", description="When each repository was fetched")
class DescribeHistoryAction(BaseAction[DescribeHistoryParams, DescribeHistoryResult]):
    """
    AI-CORE-BEGIN
    ROLE: Say what a history is before its versions are read.
    CONTRACT: An unknown history raises ``HistoryNotFoundError``; ``newest`` is the last version's sha.
    INVARIANTS: Reads only; fetches the repository only after the fallback interval.
    AI-CORE-END
    """

    @summary_aspect("Describe the history")
    @context_requires("env.history_refresh_seconds")
    async def describe_summary(
        self,
        params: DescribeHistoryParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> DescribeHistoryResult:
        """Find the history, refresh its repository, count its versions."""
        mirror = cast(GitMirror, connections["GitMirror"])
        history = found(cast(HistoriesConfig, connections["HistoriesConfig"]), params.history)
        await refreshed(mirror, cast(VersionCache, connections["VersionCache"]), history, ctx.get("env.history_refresh_seconds"))
        commits = await asyncio.to_thread(mirror.versions, history.repository, history.branch, history.graph_file)
        return DescribeHistoryResult(
            id=history.id,
            repository=history.repository,
            branch=history.branch,
            graph_file=history.graph_file,
            versions=len(commits),
            newest=commits[-1].sha if commits else None,
        )
