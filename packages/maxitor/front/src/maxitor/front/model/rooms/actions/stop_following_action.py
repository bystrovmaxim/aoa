# packages/maxitor/front/src/maxitor/front/model/rooms/actions/stop_following_action.py
"""
StopFollowingAction — a participant stops following.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Following ends on the follower's own pan, navigation, Stop or Esc (spec 028, FR-051);
the client sends this message and the room learns the new links. The view stays where
it is.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "stop_following"} ──► follows[participant] = None ──► follows to the room
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.front.model.rooms.layout_authority import recheck_layouts
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from maxitor.front.model.rooms.rooms_domain import RoomsDomain

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import SocketChannel


class StopFollowingParams(BaseParams):
    """Nothing: the follower is found by the connection."""


@meta(description="Stop following", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The follower's connection")
class StopFollowingAction(BaseAction[StopFollowingParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Remove a participant's follow link.
    CONTRACT: Announces the new follow links to the room.
    INVARIANTS: Harmless when the participant follows nobody.
    AI-CORE-END
    """

    @summary_aspect("Unlink the follower and tell the room")
    async def stop_following_summary(
        self,
        params: StopFollowingParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Clear the follow link."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        async with room.lock:
            participant.follows = None
            registry.broadcast(room, {"type": "follows", "follows": room.follows()})
            registry.send_chain_focus(room)
            recheck_layouts(room)
        return RoomAnswer()
