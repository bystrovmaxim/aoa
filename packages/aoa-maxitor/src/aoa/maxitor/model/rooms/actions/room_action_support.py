# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/room_action_support.py
"""
Room action support — the pieces every room action shares.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Room actions answer through the connection, not through their result, so they share
one empty result type. They refuse with the close codes of the room protocol
(contracts/room-protocol.md), find the room, participant and tab a message came from
by its connection — never by a value a message carries — and judge an ``Origin``
the same way.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connections["socket"] ──located()──► (Room, Participant, Tab) | refused 4404
    origin + host ──origin_allowed()──► same host, or one of the configured origins
"""

from __future__ import annotations

from urllib.parse import urlparse

from aoa.action_machine.model import BaseResult
from aoa.fastapi import ConnectionRefusalError, SocketChannel
from aoa.maxitor.model.rooms.resources.room_registry import Participant, Room, RoomRegistry, Tab

#: Close and refusal codes of the room protocol.
ORIGIN_NOT_ALLOWED = 4403
ROOM_ENDED = 4404
ROOM_FULL = 4409
INVALID_VALUE = 4422
SOURCE_UNAVAILABLE = 4502
TOO_MANY_ROOMS = 4503

#: At most this many people in one room (spec 028, FR-015).
MAX_PARTICIPANTS = 20

#: At most this many rooms open in one process (spec 028, FR-015).
MAX_ROOMS = 100


class RoomAnswer(BaseResult):
    """Room actions answer through the connection; their result carries nothing."""


def located(registry: RoomRegistry, channel: SocketChannel) -> tuple[Room, Participant, Tab]:
    """The room, participant and tab ``channel`` belongs to; refuse when it belongs to none."""
    found = registry.locate(channel)
    if found is None:
        raise ConnectionRefusalError(ROOM_ENDED, "this connection is not in a room")
    return found


def origin_allowed(origin: str, host: str, allowed: tuple[str, ...]) -> bool:
    """Whether a connection from ``origin`` may join: no origin (not a browser), the same host, or a configured one."""
    if not origin:
        return True
    if origin in allowed:
        return True
    return bool(host) and urlparse(origin).netloc == host
