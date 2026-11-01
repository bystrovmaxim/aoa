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

In Diff (spec 038, FR-016) the pick carries ``a`` as well — the older of two versions
compared — and the room's mode, A and B move as one value. A pair that breaks the range's
rules (the same version twice, Live as A, A not before B) is refused the same way; a client
puts a reversed pair in order before it sends it, so a refusal means a stale client.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "version", "b", "a"?} ──► room on a history? ──► offered? a range that holds? ──no──► {"type": "error", "reason"} to the sender
        └─ yes ──► room.version, room.version_a, room.source ──► {"type": "version", "b", "a", "by"} to the room
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.core.history_entry import HistoryEntry
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
    """The version picked — or, with ``a``, the two compared."""

    b: str = Field(min_length=1, max_length=40, description="The version: the first 12 hex characters of its commit, or 'live'")
    a: str | None = Field(default=None, max_length=40, description="In Diff, the older version compared with ``b``; absent or null for one version")
    view: str | None = Field(default=None, description="'one', 'diff' or 'split'; absent means 'diff' with ``a`` and 'one' without")


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
        reason = None
        if history is None or source is None:
            reason = "this room shows no history" if room.history is None else f"the history has no version {params.b} to show"
        elif params.a is not None:
            reason = _range_refusal(history, params.a, params.b)
        view = params.view or ("diff" if params.a is not None else "one")
        reason = reason or _view_refusal(view, params.a)
        if reason is not None:
            socket.send({"type": "error", "reason": reason})
            await box.info(Channel.business, "Version refused in room {%var.room}", room=room.id)
            return RoomAnswer()
        async with room.lock:
            room.version, room.version_a, room.view, room.source = params.b, params.a, view, cast(str, source)
            registry.broadcast(room, {"type": "version", "b": params.b, "a": params.a, "view": view, "by": participant.id})
        await box.info(Channel.business, "Room {%var.room} moved to version {%var.version}", room=room.id, version=params.b)
        return RoomAnswer()


def _view_refusal(view: str, a: str | None) -> str | None:
    """Why ``view`` cannot go with ``a`` (spec 044), or ``None`` when it can: two versions for Diff and Side by side, one for One."""
    if view not in ("one", "diff", "split"):
        return f"the room has no view {view}"
    if (view == "one") != (a is None):
        return f"{view} does not go with this many versions"
    return None


def _range_refusal(history: HistoryEntry, a: str, b: str) -> str | None:
    """Why ``a`` and ``b`` cannot be the room's two versions (spec 038, FR-011, FR-016), or ``None`` when they can."""
    if a == b:
        return "the two versions of a comparison must differ"
    if a == "live":
        return "Live can only be the newer version"
    if not history.offers(a):
        return f"the history has no version {a} to compare"
    if not history.older(a, b):
        return "the older version must come first"
    return None
