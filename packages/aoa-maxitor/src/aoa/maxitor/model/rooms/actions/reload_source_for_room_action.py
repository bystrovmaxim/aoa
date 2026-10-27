# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/reload_source_for_room_action.py
"""
ReloadSourceForRoomAction — Reload pressed inside a room rebuilds the graph for everyone.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Outside a room, Reload rebuilds the graph of one source. Inside a room it must not
split the room into people with an old and a new graph, nor make anyone leave (spec
028, FR-065): the source is rebuilt once, and every room of that source is told the
new fingerprint, so every tab re-reads the graph in place. A failed rebuild keeps the
graph everyone already has and is refused with the reason.

Until the freshness checks exist (commit 7), the rebuild goes straight through the
store's ``replace``; they will route it through the source check instead.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "reload"} ──► GraphStore.replace(room.source)
        ├─ new fingerprint ──► graph_changed to every room of the source
        └─ failure         ──► refused 4502, the old graph stays
"""

from __future__ import annotations

from typing import cast

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import ConnectionRefusalError, SocketChannel
from aoa.maxitor.api.graph_store import GraphBuildError, GraphStoreBusyError
from aoa.maxitor.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from aoa.maxitor.model.rooms.actions.room_action_support import SOURCE_UNAVAILABLE, RoomAnswer, located
from aoa.maxitor.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from aoa.maxitor.model.rooms.rooms_domain import RoomsDomain


class ReloadSourceForRoomParams(BaseParams):
    """Nothing: the room and its source are found by the connection."""


@meta(description="Rebuild a room's graph for everyone in it", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The connection that pressed Reload")
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs")
class ReloadSourceForRoomAction(BaseAction[ReloadSourceForRoomParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Rebuild the room's source once and tell every room of that source the new fingerprint.
    CONTRACT: A failed rebuild keeps the held graph and is refused with 4502; an unchanged one announces nothing.
    INVARIANTS: Nobody leaves the room; the log carries ids and the source, never names.
    AI-CORE-END
    """

    @summary_aspect("Rebuild the source and announce a changed graph")
    async def reload_summary(
        self,
        params: ReloadSourceForRoomParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Rebuild, then tell every room of the source when the graph changed."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        before = store.entry(room.source)
        try:
            entry = await store.replace(room.source)
        except (GraphBuildError, GraphStoreBusyError) as exc:
            await box.warning(Channel.error, "Reload of {%var.source} failed in room {%var.room}", source=room.source, room=room.id)
            raise ConnectionRefusalError(SOURCE_UNAVAILABLE, "the service's graph cannot be rebuilt now") from exc
        if before is not None and before.fingerprint == entry.fingerprint:
            return RoomAnswer()
        for other in registry.rooms_of_source(room.source):
            registry.broadcast(other, {"type": "graph_changed", "fingerprint": entry.fingerprint})
        await box.info(
            Channel.business,
            "Participant {%var.participant} rebuilt {%var.source} for room {%var.room}",
            participant=participant.id,
            source=room.source,
            room=room.id,
        )
        return RoomAnswer()
