# packages/maxitor/core/graph_map/src/maxitor/graph_map/places.py
"""
Places — where each area stands on the map, kept across versions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Laying the areas out anew for each version moves them all for one changed field, so
places are kept instead. An area keeps its place for as long as it fits the room reserved
for it; a new area takes the nearest free spot beside what it links to; an area that
outgrows its room moves alone; a place is never given away, so an area only an older
version has still has somewhere to stand.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    known places + radii + links ──► keep what fits ──► largest new area first ──► nearest free spot
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

RESERVE = 1.15
"""How much more room than it needs an area is given, so that it can grow in place."""

GAP = 30.0
"""The least distance between the rooms of two areas."""

GOLDEN_ANGLE = 2.399963229728653
SPIRAL_STEP = 0.35
"""How far the search for a free spot moves out per try, as a share of the area's radius."""


@dataclass(frozen=True, slots=True)
class Place:
    """Where an area stands, and how much room it has."""

    x: float
    y: float
    room: float


class _Rooms:
    """The placed rooms in a grid as coarse as the largest room, so that a spot is checked against its neighbours alone."""

    def __init__(self, largest: float) -> None:
        self._cell = 2 * largest + GAP
        self._grid: dict[tuple[int, int], list[Place]] = {}

    def _key(self, x: float, y: float) -> tuple[int, int]:
        """The cell of a point."""
        return math.floor(x / self._cell), math.floor(y / self._cell)

    def add(self, place: Place) -> None:
        """Take one room."""
        self._grid.setdefault(self._key(place.x, place.y), []).append(place)

    def free(self, x: float, y: float, room: float) -> bool:
        """Whether a room of ``room`` at ``(x, y)`` touches no placed room."""
        column, row = self._key(x, y)
        for near_column in (column - 1, column, column + 1):
            for near_row in (row - 1, row, row + 1):
                for place in self._grid.get((near_column, near_row), ()):
                    if math.hypot(place.x - x, place.y - y) < place.room + room + GAP:
                        return False
        return True


def _beside(area: str, links: Mapping[tuple[str, str], int], placed: Mapping[str, Place]) -> tuple[float, float]:
    """The middle of what ``area`` links to and is placed, weighted by the links; the map's middle when nothing is."""
    x = y = total = 0.0
    for (one, other), count in links.items():
        neighbour = placed.get(other if one == area else one) if area in (one, other) else None
        if neighbour is not None:
            x, y, total = x + neighbour.x * count, y + neighbour.y * count, total + count
    return (x / total, y / total) if total else (0.0, 0.0)


def _spot(room: float, middle: tuple[float, float], rooms: _Rooms) -> Place:
    """The nearest free spot to ``middle``, on a spiral around it."""
    step = 0
    while True:
        distance = room * SPIRAL_STEP * math.sqrt(step)
        x, y = middle[0] + distance * math.cos(step * GOLDEN_ANGLE), middle[1] + distance * math.sin(step * GOLDEN_ANGLE)
        if rooms.free(x, y, room):
            return Place(round(x, 1), round(y, 1), round(room, 1))
        step += 1


def settle_places(
    radii: Mapping[str, float],
    links: Mapping[tuple[str, str], int],
    known: Mapping[str, Place],
) -> dict[str, Place]:
    """
    AI-CORE-BEGIN
    ROLE: Give every area a place, keeping the places areas already have.
    CONTRACT: The answer holds every key of ``known`` and of ``radii``; an area in ``known`` that fits keeps its place to the digit.
    INVARIANTS: Pure; no two rooms overlap; only an area that outgrew its room moves, and it moves alone.
    AI-CORE-END
    """
    placed = {area: place for area, place in known.items() if radii.get(area, 0.0) <= place.room}
    waiting = sorted((area for area in radii if area not in placed), key=lambda area: (-radii[area], area))
    rooms = _Rooms(max([place.room for place in known.values()] + [radius * RESERVE for radius in radii.values()], default=0.0))
    for place in placed.values():
        rooms.add(place)
    for area in waiting:
        placed[area] = _spot(radii[area] * RESERVE, _beside(area, links, placed), rooms)
        rooms.add(placed[area])
    return placed
