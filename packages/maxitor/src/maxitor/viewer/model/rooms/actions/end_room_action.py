# packages/maxitor/src/maxitor/viewer/model/rooms/actions/end_room_action.py
"""
EndRoomAction — a room that stayed empty for two minutes ends.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Scheduled when the last participant leaves (spec 028, FR-014). It ends the room only
when the room is still empty and has stayed empty since that moment: someone who
joined in between keeps it open. An ended room's id is never reused, so its link says
the room has ended.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    last participant leaves ──schedule(two minutes)──► EndRoomAction(room_id, since)
        └► still empty since ``since``? ──► registry.end_room ──► log
"""

from __future__ import annotations

from typing import cast

from maxitor.viewer.model.rooms.actions.room_action_support import RoomAnswer
from maxitor.viewer.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, Room, RoomRegistry
from maxitor.viewer.model.rooms.rooms_domain import RoomsDomain
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


class EndRoomParams(BaseParams):
    """The room and the moment it became empty."""

    room_id: str = Field(description="The room to end")
    since: float = Field(description="When the room became empty, as the registry's clock read it")


@meta(description="End a room that stayed empty", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
class EndRoomAction(BaseAction[EndRoomParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: End a room whose last participant left two minutes ago and nobody came since.
    CONTRACT: Ends the room only when it is empty and ``empty_since`` still equals ``since``.
    INVARIANTS: Never ends a room someone is in; logs the end with the room id only.
    AI-CORE-END
    """

    @summary_aspect("End the room if it is still empty")
    async def end_room_summary(
        self,
        params: EndRoomParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """End the room when it stayed empty since ``params.since``."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room = registry.room(params.room_id)
        if room is None:
            return RoomAnswer()
        async with room.lock:
            if room.participants or room.empty_since != params.since:
                return RoomAnswer()
            registry.end_room(room)
        await box.info(Channel.business, "Room {%var.room} ended", room=room.id)
        return RoomAnswer()


def schedule_end_if_empty(registry: RoomRegistry, room: Room) -> None:
    """Start the countdown of an empty room; the caller holds the room's lock."""
    if room.participants:
        return
    since = registry.clock()
    room.empty_since = since
    registry.schedule(registry.empty_room_seconds, EndRoomAction, EndRoomParams(room_id=room.id, since=since))
