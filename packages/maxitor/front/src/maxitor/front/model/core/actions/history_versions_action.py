# packages/maxitor/front/src/maxitor/front/model/core/actions/history_versions_action.py
"""
HistoryVersionsAction — a held history's versions, for a tab that polls them.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A tab outside a room asks for its history's versions every 30 seconds, naming the
``ETag`` of the list it holds (spec 037, FR-006a). The server keeps the list fresh on
its own (``CheckHistoryAction``), so the answer comes from memory — when the reader's
key was accepted by the port within the last 30 seconds. Otherwise the port is asked
again with that key, which is how a revoked key stops working (FR-009). The adapter
tags the answer with an ``ETag``, so an unchanged list is answered ``304``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/history/versions?history=<name>   (X-Maxitor-History-Key, If-None-Match)
        held and (public or accepted within 30 s) ──► the held list
        otherwise ──► open_history() ──► the port's list
        either way ──► tab marked open ──► {versions, live}
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.history_reading import open_history
from maxitor.front.model.core.resources.history_access import HISTORY_ACCESS_CONNECTION_KEY, HistoryAccess
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.core.resources.open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    REPO_GRAPH_PORT_CONNECTION_KEY,
    RepoGraphPortGateway,
)
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


class HistoryVersionsParams(BaseParams):
    """The history whose versions a tab polls."""

    history: str = Field(min_length=1, description="The history's address without its key")


class HistoryVersionsResult(BaseResult):
    """The history's versions and its Live service, as held now."""

    versions: list[dict[str, Any]] = Field(description="The port's versions, oldest first")
    live: str | None = Field(default=None, description="The running service whose graph is Live, or none")


@meta(description="Answer a held history's versions to a polling tab", domain=CoreDomain)
@check_roles(GuestRole)
@connection(RepoGraphPortGateway, key=REPO_GRAPH_PORT_CONNECTION_KEY, description="Reads the history from its port")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="The histories Maxitor holds")
@connection(HistoryAccess, key=HISTORY_ACCESS_CONNECTION_KEY, description="Keys the port accepted lately")
@connection(OpenTabsRegistry, key=OPEN_TABS_CONNECTION_KEY, description="Tabs that show a history")
class HistoryVersionsAction(BaseAction[HistoryVersionsParams, HistoryVersionsResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer a polling tab its history's versions, and keep the history watched.
    CONTRACT: From memory when the key was accepted within 30 s (or the history is public); otherwise from the port, with the same refusals as ``OpenHistoryAction``.
    INVARIANTS: A key the port no longer accepts gets nothing held for someone else.
    AI-CORE-END
    """

    @summary_aspect("Answer the versions")
    @context_requires("user.history_key", "request.client_ip")
    async def versions_summary(
        self,
        params: HistoryVersionsParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> HistoryVersionsResult:
        """The held list for an accepted key, or the port's."""
        _ = state
        key = str(ctx.get("user.history_key") or "")
        store = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY])
        access = cast(HistoryAccess, connections[HISTORY_ACCESS_CONNECTION_KEY])
        entry = store.get(params.history.strip())
        if entry is None or not (entry.public or access.accepted(entry.name, key)):
            gateway = cast(RepoGraphPortGateway, connections[REPO_GRAPH_PORT_CONNECTION_KEY])
            entry = await open_history(box, gateway, store, access, params.history, key, str(ctx.get("request.client_ip") or ""))
        cast(OpenTabsRegistry, connections[OPEN_TABS_CONNECTION_KEY]).seen(entry.name, store.now())
        return HistoryVersionsResult(versions=entry.versions, live=entry.live)
