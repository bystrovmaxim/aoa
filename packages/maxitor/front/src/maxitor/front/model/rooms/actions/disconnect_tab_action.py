# packages/maxitor/front/src/maxitor/front/model/rooms/actions/disconnect_tab_action.py
"""
DisconnectTabAction — a tab's connection ended.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Runs as the WebSocket route's close action. A tab that left on purpose needs nothing
more. A tab whose connection dropped is detached: when the participant has other tabs,
the most recently active one takes over; when it was their last, they are away for two
minutes and keep their place, colour and followers (spec 028, FR-062).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connection ends ──► DisconnectTabAction
        ├─ left on purpose ──► nothing
        ├─ other tabs      ──► presence
        └─ last tab        ──► away until now + window ──► presence ──► schedule expiry
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.rooms.actions.expire_participant_action import (
    ExpireParticipantAction,
    ExpireParticipantParams,
)
from maxitor.front.model.rooms.actions.room_action_support import RoomAnswer
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


class DisconnectTabParams(BaseParams):
    """Nothing: the tab is found by its connection."""


@meta(description="Detach a tab whose connection ended", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The tab's connection")
class DisconnectTabAction(BaseAction[DisconnectTabParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Turn a dropped connection into a detached tab, or an away participant with a return window.
    CONTRACT: Ignores tabs that left on purpose; opens the window only when the participant's last tab drops.
    INVARIANTS: Never removes the participant itself; that is ExpireParticipantAction's decision.
    AI-CORE-END
    """

    @summary_aspect("Detach the tab and open the return window when it was the last")
    async def disconnect_summary(
        self,
        params: DisconnectTabParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Detach the tab; start the return window when no tab of the participant is left."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        found = registry.locate(cast(SocketChannel, connections["socket"]))
        if found is None:
            return RoomAnswer()
        room, participant, tab = found
        async with room.lock:
            if tab.leaving:
                return RoomAnswer()
            registry.remove_tab(participant, tab.id)
            if not participant.tabs:
                until = registry.clock() + registry.return_window_seconds
                participant.return_until = until
                registry.schedule(
                    registry.return_window_seconds,
                    ExpireParticipantAction,
                    ExpireParticipantParams(room_id=room.id, participant=participant.id, until=until),
                )
            registry.broadcast(room, {"type": "presence", **participant.public()}, except_participant=participant.id)
            recheck_layouts(room)
        if participant.away:
            await box.info(
                Channel.business,
                "Participant {%var.participant} lost the connection to room {%var.room}",
                participant=participant.id,
                room=room.id,
            )
        return RoomAnswer()
