# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/rename_participant_action.py
"""
RenameParticipantAction — a participant changes their name.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The new name reaches everyone at once and the colour stays (spec 028, FR-061). A name
is 1–40 characters after trimming; anything else is refused and the old name stays.
The log says that a participant was renamed, never what they are called.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "rename", "name"} ──► valid? ──► participant.name ──► renamed to the room
"""

from __future__ import annotations

from typing import cast

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
from aoa.fastapi import ConnectionRefusalError, SocketChannel
from aoa.maxitor.model.rooms.actions.room_action_support import INVALID_VALUE, RoomAnswer, located
from aoa.maxitor.model.rooms.pages import name_error
from aoa.maxitor.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from aoa.maxitor.model.rooms.rooms_domain import RoomsDomain


class RenameParticipantParams(BaseParams):
    """The new name."""

    name: str = Field(description="The name the participant typed")


@meta(description="Change a participant's name", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The participant's connection")
class RenameParticipantAction(BaseAction[RenameParticipantParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Rename a participant, keeping their colour.
    CONTRACT: Refuses a name that is not 1–40 characters after trimming with 4422.
    INVARIANTS: The name never reaches the log.
    AI-CORE-END
    """

    @summary_aspect("Validate the name and tell the room")
    async def rename_summary(
        self,
        params: RenameParticipantParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Set the new name and announce it."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        if name_error(params.name):
            raise ConnectionRefusalError(INVALID_VALUE, "invalid name")
        async with room.lock:
            participant.name = params.name.strip()
            registry.broadcast(room, {"type": "renamed", "participant": participant.id, "name": participant.name})
        await box.info(
            Channel.business,
            "Participant {%var.participant} renamed in room {%var.room}",
            participant=participant.id,
            room=room.id,
        )
        return RoomAnswer()
