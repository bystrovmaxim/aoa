# packages/maxitor/front/src/maxitor/front/model/rooms/actions/reload_source_for_room_action.py
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

It runs ``CheckSourceAction`` with ``force``: the same rebuild the freshness checks do, so a
Reload and a check of one source never overlap.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "reload"} ──► CheckSourceAction(room.source, force=True)
        ├─ rebuilt ──► graph_changed to every room of the source (by the check)
        └─ failed  ──► refused 4502, the old graph stays
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.core.actions.check_source_action import CheckSourceAction, CheckSourceParams
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.rooms.actions.room_action_support import SOURCE_UNAVAILABLE, RoomAnswer, located
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from maxitor.front.model.rooms.rooms_domain import RoomsDomain

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


class ReloadSourceForRoomParams(BaseParams):
    """Nothing: the room and its source are found by the connection."""


@meta(description="Rebuild a room's graph for everyone in it", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The connection that pressed Reload")
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs")
@connection(GraphSourceGateway, key=GRAPH_SOURCE_CONNECTION_KEY, description="Downloads graph-json")
class ReloadSourceForRoomAction(BaseAction[ReloadSourceForRoomParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Rebuild the room's source once and tell every room of that source the new fingerprint.
    CONTRACT: A failed rebuild keeps the held graph and is refused with 4502; the check announces a changed graph.
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
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        result = await box.run(
            CheckSourceAction,
            CheckSourceParams(source=room.source, force=True),
            {
                GRAPH_STORE_CONNECTION_KEY: connections[GRAPH_STORE_CONNECTION_KEY],
                GRAPH_SOURCE_CONNECTION_KEY: connections[GRAPH_SOURCE_CONNECTION_KEY],
                ROOM_REGISTRY_KEY: registry,
            },
        )
        if result.status == "failed":
            raise ConnectionRefusalError(SOURCE_UNAVAILABLE, "the service's graph cannot be rebuilt now")
        await box.info(
            Channel.business,
            "Participant {%var.participant} reloaded {%var.source} for room {%var.room}",
            participant=participant.id,
            source=room.source,
            room=room.id,
        )
        return RoomAnswer()
