# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/actions/receive_host_event_action.py
"""
ReceiveHostEventAction — a GitHub webhook refreshes the histories it changes, and only them.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One repository may hold several graph files, and most pushes and pull requests
touch none of them. An event names a repository; git, not the event's own file
lists (a push lists at most 20 commits), decides which of that repository's
configured histories it changes. The answer names them.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    push (repository, branch, before, after) ──► the histories of that repository and branch
        ──► one fetch ──► changed: those whose graph file changed by first parent between before and after
    tag (repository) ──► one fetch; its releases forgotten ──► changed: every history of the repository
    pull_request (repository, merge commit) ──► one fetch ──► changed: the histories that have that commit
        as a version; that version's pull request forgotten
    other, or a repository no history names ──► nothing

The signature is checked before the action, by the server's middleware; no graph
file is read here — the next read of a history reads what is new.
"""

from __future__ import annotations

import asyncio
from typing import cast

from maxitor.repo_graph_port.history_reading import refreshed
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class ReceiveHostEventParams(BaseParams):
    """What the event says, reduced to what the port reads."""

    kind: str = Field(description="push, tag, pull_request or other")
    repository: str = Field(description="owner/name of the repository the event is about")
    ref: str = Field(default="", description="The pushed ref, refs/heads/<branch>")
    before: str = Field(default="", description="The branch's commit before a push")
    after: str = Field(default="", description="The branch's commit after a push")
    merge_commit_sha: str = Field(default="", description="The commit a merged or edited pull request made")


class ReceiveHostEventResult(BaseResult):
    """The histories the event changed."""

    changed: list[str] = Field(description="Ids of the configured histories the event changed, sorted")


@meta(description="Refresh the histories a GitHub webhook changes", domain=RepoGraphDomain)
@check_roles(GuestRole)
@connection(HistoriesConfig, key="HistoriesConfig", description="The histories of the event's repository")
@connection(GitMirror, key="GitMirror", description="The repository's mirror, fetched once")
@connection(GitHubHost, key="GitHubHost", description="The App's token for the fetch")
@connection(VersionCache, key="VersionCache", description="Pull requests and releases to forget")
class ReceiveHostEventAction(BaseAction[ReceiveHostEventParams, ReceiveHostEventResult]):
    """
    AI-CORE-BEGIN
    ROLE: Turn a host's event into fresh histories, touching only those it changes.
    CONTRACT: Fetches the event's repository at most once; returns the ids of the configured histories it changed; reads no graph file.
    INVARIANTS: Trusts the event only because the server checked its signature first.
    AI-CORE-END
    """

    @summary_aspect("Refresh the histories the event changed")
    async def receive_summary(
        self,
        params: ReceiveHostEventParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ReceiveHostEventResult:
        """Find the event's histories, fetch once, say which changed."""
        config = cast(HistoriesConfig, connections["HistoriesConfig"])
        mirror = cast(GitMirror, connections["GitMirror"])
        cache = cast(VersionCache, connections["VersionCache"])
        branch = params.ref.removeprefix("refs/heads/") if params.kind == "push" else None
        histories = config.histories_of(params.repository, branch) if params.kind != "other" else []
        if not histories:
            return ReceiveHostEventResult(changed=[])
        await refreshed(mirror, cache, cast(GitHubHost, connections["GitHubHost"]), histories[0], 0)
        changed: list[str] = []
        for history in histories:
            if params.kind == "push":
                moved = await asyncio.to_thread(mirror.changed, history.repository, params.before, params.after, history.graph_file)
            elif params.kind == "tag":
                cache.forget_releases(history.repository)
                moved = True
            else:
                versions = await asyncio.to_thread(mirror.versions, history.repository, history.branch, history.graph_file)
                moved = params.merge_commit_sha in {commit.sha for commit in versions}
                if moved:
                    cache.forget_pull_request(history.repository, params.merge_commit_sha)
            if moved:
                changed.append(history.id)
        await box.info(Channel.business, "Event {%var.kind} on {%var.repository} changed {%var.changed}", kind=params.kind, repository=params.repository, changed=", ".join(changed) or "nothing")
        return ReceiveHostEventResult(changed=changed)
