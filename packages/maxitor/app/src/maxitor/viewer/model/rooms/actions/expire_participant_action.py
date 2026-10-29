# packages/maxitor/app/src/maxitor/viewer/model/rooms/actions/expire_participant_action.py
"""
ExpireParticipantAction — someone who lost the connection and did not come back leaves.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Scheduled when a participant's last connection drops (spec 028, FR-062). When the
window ends and they have not reconnected, they leave the room as if they had pressed
Leave: their circle goes, their colour is freed, everyone following them stops, and an
empty room starts its own countdown.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    last tab lost ──schedule(window)──► ExpireParticipantAction(room, participant, until)
        └► still away with that deadline? ──► remove ──► left + follows ──► empty? countdown
"""

from __future__ import annotations

from typing import cast

from maxitor.viewer.model.rooms.actions.end_room_action import schedule_end_if_empty
from maxitor.viewer.model.rooms.actions.room_action_support import RoomAnswer
from maxitor.viewer.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
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


class ExpireParticipantParams(BaseParams):
    """The participant whose return window ends."""

    room_id: str = Field(description="The participant's room")
    participant: str = Field(description="The participant who lost the connection")
    until: float = Field(description="The end of their return window, as the registry's clock read it")


@meta(description="Remove a participant who did not come back in time", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
class ExpireParticipantAction(BaseAction[ExpireParticipantParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: End the return window of a participant who lost every connection.
    CONTRACT: Removes the participant only when they are still away with the same deadline.
    INVARIANTS: A participant who came back is never removed; the log carries ids only.
    AI-CORE-END
    """

    @summary_aspect("Remove the participant if they are still away")
    async def expire_summary(
        self,
        params: ExpireParticipantParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Remove the participant when their window ended without a return."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room = registry.room(params.room_id)
        if room is None:
            return RoomAnswer()
        async with room.lock:
            participant = room.participants.get(params.participant)
            if participant is None or participant.tabs or participant.return_until != params.until:
                return RoomAnswer()
            registry.remove_participant(room, participant.id)
            registry.broadcast(room, {"type": "left", "participant": participant.public()})
            registry.broadcast(room, {"type": "follows", "follows": room.follows()})
            schedule_end_if_empty(registry, room)
        await box.info(
            Channel.business,
            "Participant {%var.participant} left room {%var.room} after losing the connection",
            participant=participant.id,
            room=room.id,
        )
        return RoomAnswer()
