# packages/maxitor/front/src/maxitor/front/model/core/actions/check_history_action.py
"""
CheckHistoryAction — ask a held history's port whether its list or its Live changed, and tell its rooms.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history's list of versions is checked on the freshness schedule, like a source with
validators (spec 037, FR-006a): the port is asked with the held ``ETag``, so an unchanged
list costs a ``304``. The port's description is read too, since ``live`` can be added to or
removed from its config. When anything changed, the held history is replaced and every
room on it is told ``history_changed``; a room whose version is gone, or on Live that is
no longer there, moves as one to the history's default version (the spec's edge cases).

A private history is read with a key the port still accepts (research R18): the newest
one remembered first; one the port refuses is dropped, and when none is left every room
on the history is told "not found".

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    held history ──► each remembered key (none for a public one)
        └─ port.versions(etag) ──► 304 ──► describe: live changed? ──► rooms told
                              └─ 200 ──► describe ──► entry replaced ──► rooms told, moved if needed
                              └─ 404 ──► key dropped ──► next key; none left ──► rooms told "not found"
"""

from __future__ import annotations

from typing import Literal, cast

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.history_entry import HistoryEntry
from maxitor.front.model.core.history_reading import history_line
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    REPO_GRAPH_PORT_CONNECTION_KEY,
    Described,
    Listed,
    PortNotFound,
    PortNotModified,
    RepoGraphPortGateway,
)
from maxitor.front.model.core.source_label import label
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
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

#: What one check of a history found.
HistoryCheckStatus = Literal["not_held", "skipped", "unchanged", "changed", "unreachable", "not_found"]


class CheckHistoryParams(BaseParams):
    """The held history to check."""

    history: str = Field(min_length=1, description="The history's address without its key")


class CheckHistoryResult(BaseResult):
    """What the check found."""

    status: HistoryCheckStatus = Field(description="not_held, skipped, unchanged, changed, unreachable or not_found")


@meta(description="Ask a held history's port whether its list or its Live changed, and tell its rooms", domain=CoreDomain)
@check_roles(GuestRole)
@connection(RepoGraphPortGateway, key=REPO_GRAPH_PORT_CONNECTION_KEY, description="Reads the history from its port")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="The histories Maxitor holds")
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Rooms on the history")
class CheckHistoryAction(BaseAction[CheckHistoryParams, CheckHistoryResult]):
    """
    AI-CORE-BEGIN
    ROLE: Keep a held history's list and Live current, and keep its rooms on a version it still has.
    CONTRACT: One check per call; never two at once for one history; ``last_checked`` moves whatever the outcome.
    INVARIANTS: Reads with remembered keys only; names the history by its id and key's name, the port by its label.
    AI-CORE-END
    """

    @summary_aspect("Check the history and tell its rooms")
    async def check_summary(
        self,
        params: CheckHistoryParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CheckHistoryResult:
        """Check the history once."""
        _ = state
        store = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY])
        entry = store.peek(params.history)
        if entry is None:
            return CheckHistoryResult(status="not_held")
        if entry.checking:
            return CheckHistoryResult(status="skipped")
        entry.checking = True
        try:
            status = await _check(entry, cast(RepoGraphPortGateway, connections[REPO_GRAPH_PORT_CONNECTION_KEY]), cast(RoomRegistry, connections[ROOM_REGISTRY_KEY]), box)
        finally:
            entry.checking = False
            entry.last_checked = store.now()
        return CheckHistoryResult(status=status)


async def _check(entry: HistoryEntry, gateway: RepoGraphPortGateway, rooms: RoomRegistry, box: ToolsBox) -> HistoryCheckStatus:
    """Ask the port with each remembered key in turn; apply what it says."""
    for key in [""] if entry.public else list(entry.keys):
        listed = await gateway.versions(entry.route, entry.link, key, entry.etag)
        if isinstance(listed, PortNotFound):
            entry.forget(key)
            await box.warning(Channel.security, "{%var.history} at {%var.port}: the port no longer accepts a key Maxitor held", history=history_line(entry), port=label(entry.route))
            continue
        if not isinstance(listed, Listed | PortNotModified):
            await box.warning(Channel.business, "{%var.history} at {%var.port} not checked: the port cannot be read now", history=history_line(entry), port=label(entry.route))
            return "unreachable"
        described = await gateway.describe(entry.route, entry.link, key)
        live = described.body.get("live") if isinstance(described, Described) and not entry.public else entry.live
        live = live if isinstance(live, str) else None
        if isinstance(listed, PortNotModified) and live == entry.live:
            await box.info(Channel.business, "{%var.history} unchanged", history=history_line(entry))
            return "unchanged"
        if isinstance(listed, Listed):
            entry.versions, entry.etag = listed.versions, listed.etag
        entry.live = live
        _tell_rooms(entry, rooms)
        await box.info(Channel.business, "{%var.history} changed: {%var.count} versions{%var.live}", history=history_line(entry), count=len(entry.versions), live=" and Live" if entry.live else "")
        return "changed"
    for room in rooms.rooms_of_history(entry.name):
        rooms.broadcast(room, {"type": "refused", "code": 4404, "reason": "not found"})
    return "not_found"


def _tell_rooms(entry: HistoryEntry, rooms: RoomRegistry) -> None:
    """Tell every room on the history that it changed; move a room whose version it no longer offers."""
    for room in rooms.rooms_of_history(entry.name):
        rooms.broadcast(room, {"type": "history_changed"})
        if room.version is not None and entry.offers(room.version):
            continue
        moved = entry.default_version()
        source = entry.source_of(moved) if moved is not None else None
        room.version = moved
        if source is not None:
            room.source = source
        rooms.broadcast(room, {"type": "version", "b": moved, "by": None})
