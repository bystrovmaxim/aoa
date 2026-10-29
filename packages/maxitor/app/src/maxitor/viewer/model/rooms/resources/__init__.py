# packages/maxitor/app/src/maxitor/viewer/model/rooms/resources/__init__.py
"""
Maxitor rooms — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the room registry room actions use for ``@connection`` wiring.
"""

from .room_registry import PALETTE, ROOM_REGISTRY_KEY, Participant, Room, RoomRegistry, Tab

__all__ = ["PALETTE", "ROOM_REGISTRY_KEY", "Participant", "Room", "RoomRegistry", "Tab"]
