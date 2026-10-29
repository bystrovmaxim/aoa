# packages/maxitor/front/src/maxitor/front/model/rooms/actions/set_room_version_action.py
"""
SetRoomVersionAction — someone in a room on a history picks another version, and the whole room moves.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

In a room on a history the version belongs to the room, like a page's filters and layout
mode (spec 037, FR-022a; spec 028, FR-030, FR-031): a pick by anyone changes it for
everyone, sent as a value, never a step, so two picks at once end with the last one. A
version the history does not have, a refused one, or Live where there is none is refused
to the participant who picked it alone, with the reason, and the room does not move.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "version", "b"} ──► room on a history? ──► offered? ──no──► {"type": "error", "reason"} to the sender
        └─ yes ──► room.version, room.source ──► {"type": "version", "b", "by"} to the room
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from maxitor.front.model.rooms.rooms_domain import RoomsDomain
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import SocketChannel


class SetRoomVersionParams(BaseParams):
    """The version picked."""

    b: str = Field(min_length=1, max_length=40, description="The version: the first 12 hex characters of its commit, or 'live'")


@meta(description="Move a room on a history to another version", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The participant's connection")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="The histories Maxitor holds")
class SetRoomVersionAction(BaseAction[SetRoomVersionParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Set the version of a room on a history and tell everyone.
    CONTRACT: An offered version moves the room and is broadcast with who picked it; anything else is an ``error`` to the sender only.
    INVARIANTS: The last pick wins; the room's ``source`` is always the graph of its ``version``.
    AI-CORE-END
    """

    @summary_aspect("Move the room or refuse the pick")
    async def version_summary(
        self,
        params: SetRoomVersionParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Move the room to the picked version, or tell the picker why not."""
        _ = state
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        socket = cast(SocketChannel, connections["socket"])
        room, participant, _ = located(registry, socket)
        history = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY]).peek(room.history) if room.history else None
        source = history.source_of(params.b) if history is not None else None
        if history is None or source is None:
            reason = "this room shows no history" if room.history is None else f"the history has no version {params.b} to show"
            socket.send({"type": "error", "reason": reason})
            await box.info(Channel.business, "Version refused in room {%var.room}", room=room.id)
            return RoomAnswer()
        async with room.lock:
            room.version, room.source = params.b, source
            registry.broadcast(room, {"type": "version", "b": params.b, "by": participant.id})
        await box.info(Channel.business, "Room {%var.room} moved to version {%var.version}", room=room.id, version=params.b)
        return RoomAnswer()
