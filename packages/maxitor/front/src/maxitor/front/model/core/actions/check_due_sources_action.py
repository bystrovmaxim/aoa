# packages/maxitor/front/src/maxitor/front/model/core/actions/check_due_sources_action.py
"""
CheckDueSourcesAction — check every held source someone is looking at and that is due.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Run every ten seconds by the ``SourceChecks`` clock (spec 028, FR-071, FR-073). A held source is
picked when someone looks at it — a room of that source has a connected participant, or a tab
outside a room asked for its fingerprint in the last 75 seconds — and its last check is older
than its interval (30 s with validators, 2 min without). Each picked source gets one
``CheckSourceAction``; a source without open tabs waits for its next read. A held history
(spec 037, FR-006a) is picked the same way — a room on it, or a tab that polled it — every
30 seconds, and gets one ``CheckHistoryAction``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    held sources ──open tab? due?──► CheckSourceAction × n (box.run, side by side)
"""

from __future__ import annotations

import asyncio
from typing import cast

from maxitor.front.model.core.actions.check_history_action import CheckHistoryAction, CheckHistoryParams
from maxitor.front.model.core.actions.check_source_action import CheckSourceAction, CheckSourceParams
from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.freshness import CHECK_WITH_VALIDATORS_SECONDS, is_due, tab_is_open
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.core.resources.open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    REPO_GRAPH_PORT_CONNECTION_KEY,
    RepoGraphPortGateway,
)
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class CheckDueSourcesResult(BaseResult):
    """The sources checked this round."""

    checked: list[str] = Field(description="Sources and histories a check was run for")


def _history_watched(name: str, rooms: RoomRegistry, tabs: OpenTabsRegistry, now: float) -> bool:
    """Whether someone looks at the history ``name``: a connected participant in one of its rooms, or a recent tab."""
    in_room = any(participant.tabs for room in rooms.rooms_of_history(name) for participant in room.participants.values())
    return in_room or tab_is_open(tabs.last_seen(name), now)


def _watched(source: str, rooms: RoomRegistry, tabs: OpenTabsRegistry, now: float) -> bool:
    """Whether someone looks at ``source``: a connected participant in one of its rooms, or a recent tab."""
    in_room = any(participant.tabs for room in rooms.rooms_of_source(source) for participant in room.participants.values())
    return in_room or tab_is_open(tabs.last_seen(source), now)


@meta(description="Check every held source that someone looks at and that is due", domain=CoreDomain)
@check_roles(GuestRole)
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs")
@connection(GraphSourceGateway, key=GRAPH_SOURCE_CONNECTION_KEY, description="Downloads graph-json")
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Rooms, whose participants are open tabs")
@connection(OpenTabsRegistry, key=OPEN_TABS_CONNECTION_KEY, description="Tabs outside rooms")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="Held histories, whose lists are checked too")
@connection(RepoGraphPortGateway, key=REPO_GRAPH_PORT_CONNECTION_KEY, description="Reads a history from its port")
class CheckDueSourcesAction(BaseAction[ParamsStub, CheckDueSourcesResult]):
    """
    AI-CORE-BEGIN
    ROLE: Pick the held sources that are watched and due, and check each once.
    CONTRACT: Watched = a connected participant in one of its rooms, or a tab seen within 75 s; due =
    last check older than 30 s (validators) or 120 s (none) with no check running.
    INVARIANTS: An unwatched source is never checked here; a running check is never doubled.
    AI-CORE-END
    """

    @summary_aspect("Pick watched, due sources and check them")
    async def check_due_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CheckDueSourcesResult:
        """Check every watched source whose check is due."""
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        rooms = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        tabs = cast(OpenTabsRegistry, connections[OPEN_TABS_CONNECTION_KEY])
        now = store.now()
        due = []
        for source in store.held_sources():
            entry = store.entry(source)
            if entry is not None and is_due(entry, now) and _watched(source, rooms, tabs, now):
                due.append(source)
        check_connections = {
            GRAPH_STORE_CONNECTION_KEY: store,
            GRAPH_SOURCE_CONNECTION_KEY: connections[GRAPH_SOURCE_CONNECTION_KEY],
            ROOM_REGISTRY_KEY: rooms,
        }
        histories = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY])
        due_histories = [
            name
            for name in histories.names()
            if (history := histories.peek(name)) is not None
            and not history.checking
            and now - history.last_checked >= CHECK_WITH_VALIDATORS_SECONDS
            and _history_watched(name, rooms, tabs, now)
        ]
        history_connections = {
            HISTORY_STORE_CONNECTION_KEY: histories,
            REPO_GRAPH_PORT_CONNECTION_KEY: connections[REPO_GRAPH_PORT_CONNECTION_KEY],
            ROOM_REGISTRY_KEY: rooms,
        }
        await asyncio.gather(
            *(box.run(CheckSourceAction, CheckSourceParams(source=source), check_connections) for source in due),
            *(box.run(CheckHistoryAction, CheckHistoryParams(history=name), history_connections) for name in due_histories),
        )
        return CheckDueSourcesResult(checked=due + due_histories)
