# packages/maxitor/front/src/maxitor/front/model/rooms/actions/leave_room_action.py
"""
LeaveRoomAction — a participant presses Leave room.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The participant leaves for good (spec 028, FR-019): every tab of theirs is closed,
their circle goes, their colour is freed, everyone following them stops, and a room
left empty starts its countdown. The page they were on stays as it was; the client
removes ``room`` from the address.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "leave"} ──► LeaveRoomAction ──► remove participant (tabs closed)
        └► left + follows to the room ──► empty? schedule EndRoomAction
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.rooms.actions.end_room_action import schedule_end_if_empty
from maxitor.front.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.front.model.rooms.layout_authority import recheck_layouts
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
from aoa.fastapi import SocketChannel


class LeaveRoomParams(BaseParams):
    """Nothing: the participant is found by the connection."""


@meta(description="Leave a room for good", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The leaving tab's connection")
class LeaveRoomAction(BaseAction[LeaveRoomParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Remove a participant who chose to leave, with all their tabs.
    CONTRACT: Announces ``left`` and the new follow links; an emptied room starts its countdown.
    INVARIANTS: The log carries ids only.
    AI-CORE-END
    """

    @summary_aspect("Remove the participant and tell the room")
    async def leave_summary(
        self,
        params: LeaveRoomParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Remove the participant, close their tabs, and tell everyone else."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        async with room.lock:
            registry.remove_participant(room, participant.id)
            registry.broadcast(room, {"type": "left", "participant": participant.public()})
            registry.broadcast(room, {"type": "follows", "follows": room.follows()})
            recheck_layouts(room)
            schedule_end_if_empty(registry, room)
        await box.info(
            Channel.business,
            "Participant {%var.participant} left room {%var.room}",
            participant=participant.id,
            room=room.id,
        )
        return RoomAnswer()
