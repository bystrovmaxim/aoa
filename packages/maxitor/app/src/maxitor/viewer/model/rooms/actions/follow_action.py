# packages/maxitor/app/src/maxitor/viewer/model/rooms/actions/follow_action.py
"""
FollowAction — a participant starts following someone, unless it would close a circle.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Following makes the follower's screen go wherever the followed person goes (spec 028,
FR-051, FR-053). It may never close a circle — two screens chasing each other —
directly or through others (FR-054). The rule is checked and the link written under
the room's lock, so two people pressing Follow on each other at the same moment
cannot both succeed: the second is refused with the reason.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "follow", "target"} ──► lock ──► present? not self? no circle?
        ├─ yes ──► follows[participant] = target ──► follows to the room
        │          └─► the target's last focus to the follower (spec 029, FR-010)
        └─ no  ──► follow_refused to the tab ──► security warning
"""

from __future__ import annotations

from typing import cast

from maxitor.viewer.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.viewer.model.rooms.follow_circle import would_close_circle
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
from aoa.fastapi import SocketChannel


class FollowParams(BaseParams):
    """Who to follow."""

    target: str = Field(min_length=1, description="The participant to follow")


@meta(description="Start following another participant", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The follower's connection")
class FollowAction(BaseAction[FollowParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Link a follower to the person they follow, never closing a circle.
    CONTRACT: Refuses (``follow_refused``) an absent target, oneself, or a target whose own links lead back.
    INVARIANTS: The circle check and the write happen under the room's lock; one person follows at most one.
    AI-CORE-END
    """

    @summary_aspect("Check the circle rule and link, or refuse")
    async def follow_summary(
        self,
        params: FollowParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Link the follower or tell them why not."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        socket = cast(SocketChannel, connections["socket"])
        room, participant, _ = located(registry, socket)
        async with room.lock:
            reason = None
            if params.target == participant.id or params.target not in room.participants:
                reason = "you cannot follow this participant"
            elif would_close_circle(room.follows(), participant.id, params.target):
                reason = "they already follow you, directly or through others"
            if reason is None:
                participant.follows = params.target
                registry.broadcast(room, {"type": "follows", "follows": room.follows()})
                registry.send_focus(participant, room.participants[params.target])
        if reason is not None:
            socket.send({"type": "follow_refused", "target": params.target, "reason": reason})
            await box.warning(
                Channel.security,
                "Follow refused in room {%var.room}: {%var.participant} to {%var.target}",
                room=room.id,
                participant=participant.id,
                target=params.target,
            )
            return RoomAnswer()
        await box.info(
            Channel.business,
            "Participant {%var.participant} follows {%var.target} in room {%var.room}",
            participant=participant.id,
            target=params.target,
            room=room.id,
        )
        return RoomAnswer()
