# packages/maxitor/front/src/maxitor/front/model/core/actions/open_history_action.py
"""
OpenHistoryAction — open a history through its port: what it is, its versions, and a room ticket.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The browser opens a history by its name — the address without its key — and sends the
key, if any, in a header (spec 037, FR-001, FR-010b). This action reads the history
through its port, holds it for every reader, and answers what the screen needs: the
history's title, its repository and host, its Live service, its versions, and for a
private history a one-use ticket into a room (research R18).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/history/open?history=<name>   (X-Maxitor-History-Key)
        └──► open_history() ──► HistoryEntry held ──► tab marked open ──► {name, title, host, repository, live, versions, count, room_ticket}
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.history_reading import history_line, open_history
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
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class OpenHistoryParams(BaseParams):
    """The history to open, by its name."""

    history: str = Field(min_length=1, description="The history's address without its key: a port's history URL, or a GitHub link to a graph file")


class OpenHistoryResult(BaseResult):
    """What the screen needs to show the history."""

    name: str = Field(description="The history's address without its key")
    title: str = Field(description="The history's id, or owner/repo for a public one")
    host: str = Field(description="github or local: whether #123 in a message is a pull request on GitHub")
    repository: str = Field(description="owner/name on the host, or a path on the port's disk")
    live: str | None = Field(default=None, description="The running service whose graph is Live, or none")
    versions: list[dict[str, Any]] = Field(description="The port's versions, oldest first")
    count: int = Field(ge=0, description="How many versions there are")
    room_ticket: str | None = Field(default=None, description="A one-use ticket into a room of this history, for a private one")


@meta(description="Open a history through its port and hold it", domain=CoreDomain)
@check_roles(GuestRole)
@connection(RepoGraphPortGateway, key=REPO_GRAPH_PORT_CONNECTION_KEY, description="Reads the history from its port")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="The histories Maxitor holds")
@connection(HistoryAccess, key=HISTORY_ACCESS_CONNECTION_KEY, description="Keys the port accepted lately, room tickets")
@connection(OpenTabsRegistry, key=OPEN_TABS_CONNECTION_KEY, description="Tabs that show a history")
class OpenHistoryAction(BaseAction[OpenHistoryParams, OpenHistoryResult]):
    """
    AI-CORE-BEGIN
    ROLE: Open a history for a reader and hold it for everyone.
    CONTRACT: Answers the history as its port described and listed it; a refusal ends in ``HistoryNotFoundError``, ``TooManyWrongKeysError`` or ``HistoryUnreachableError``, an address out of shape in ``HistoryAddressError`` or ``PublicHistoriesNotSetUpError``.
    INVARIANTS: The key comes only from the context and goes only to the port; the log names the history by its id and the key's name.
    AI-CORE-END
    """

    @summary_aspect("Open the history and answer it")
    @context_requires("user.history_key", "request.client_ip")
    async def open_summary(
        self,
        params: OpenHistoryParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> OpenHistoryResult:
        """Read the history through its port, hold it, and answer it with a room ticket."""
        _ = state
        key = str(ctx.get("user.history_key") or "")
        store = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY])
        access = cast(HistoryAccess, connections[HISTORY_ACCESS_CONNECTION_KEY])
        gateway = cast(RepoGraphPortGateway, connections[REPO_GRAPH_PORT_CONNECTION_KEY])
        entry = await open_history(box, gateway, store, access, params.history, key, str(ctx.get("request.client_ip") or ""))
        cast(OpenTabsRegistry, connections[OPEN_TABS_CONNECTION_KEY]).seen(entry.name, store.now())
        await box.info(Channel.business, "{%var.history} opened: {%var.count} versions{%var.live}", history=history_line(entry), count=len(entry.versions), live=" and Live" if entry.live else "")
        return OpenHistoryResult(
            name=entry.name,
            title=entry.title,
            host=entry.host,
            repository=entry.repository,
            live=entry.live,
            versions=entry.versions,
            count=len(entry.versions),
            room_ticket=None if entry.public else access.issue_ticket(entry.name, key),
        )
