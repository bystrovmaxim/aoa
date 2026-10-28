# packages/maxitor/src/maxitor/viewer/model/rooms/rooms_domain.py
"""
RoomsDomain — bounded-context marker for looking at one service together.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declares the domain of Maxitor's rooms: opening and joining a room, the shared
settings of its pages, pointers, and following someone. Every room action and the
room registry carry it, so the rooms appear as one domain on Maxitor's own graph.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class RoomsDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Marker domain for Maxitor rooms — people looking at one service together.
    CONTRACT: ``name`` is ``rooms``; use with ``@meta(domain=RoomsDomain)``.
    INVARIANTS: Marker only — no I/O on the class.
    AI-CORE-END
    """

    name = "rooms"
    description = "Rooms: people looking at one service together, with shared settings, pointers and following"
