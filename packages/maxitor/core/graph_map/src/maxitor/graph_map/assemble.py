# packages/maxitor/core/graph_map/src/maxitor/graph_map/assemble.py
"""
Assemble — the overview of a version's map, and the detail of each area.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The overview is all the browser reads first, so it carries what a filter needs without
another read: counts by type, each bundle's links by the types of their ends, and a
sketch per area, a coarse grid of counts that an outline can be drawn from with no node
in the browser. An area's detail holds its nodes, its links and its links to other areas.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GraphAreas + layouts + places ──► overview {areas, bundles, shared, types}
                                  └─► details {area id: {nodes, edges, across}}
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from maxitor.graph_map.areas import Area, GraphAreas, MapEdge
from maxitor.graph_map.layout import AreaLayout
from maxitor.graph_map.places import Place

SKETCH_CELLS = 16
"""How many cells a sketch has across."""

MIN_SKETCH_CELL = 60.0
"""A sketch's cell is never finer than this, in map units."""


@dataclass(frozen=True, slots=True)
class VersionMap:
    """What a version's map is read from."""

    overview: dict[str, Any]
    details: dict[str, dict[str, Any]]


def _sketch(area: Area, layout: AreaLayout, types: Sequence[str]) -> dict[str, Any]:
    """A coarse grid of the area's nodes by type: cells are ``[column, row, type index, count]``, around its centre."""
    cell = max(MIN_SKETCH_CELL, 2 * layout.radius / SKETCH_CELLS)
    counts: dict[tuple[int, int, int], int] = {}
    for node in area.nodes:
        x, y = layout.positions[node.id]
        key = (int(x // cell), int(y // cell), types.index(node.type))
        counts[key] = counts.get(key, 0) + 1
    return {"cell": round(cell, 1), "cells": [[*key, count] for key, count in sorted(counts.items())]}


def _edge(edge: MapEdge, levels: Mapping[str, int]) -> dict[str, Any]:
    """One link as an area's detail lists it, with the level from which both its ends show."""
    return {"id": edge.id, "source": edge.source, "target": edge.target, "type": edge.type, "level": max(levels[edge.source], levels[edge.target])}


def _detail(area: Area, layout: AreaLayout, place: Place, levels: Mapping[str, int]) -> dict[str, Any]:
    """One area's nodes at their places on the map, and its links."""
    nodes = []
    for node in area.nodes:
        x, y = layout.positions[node.id]
        nodes.append({"id": node.id, "label": node.label, "type": node.type, "level": node.level, "x": round(place.x + x, 1), "y": round(place.y + y, 1)})
    return {"nodes": nodes, "edges": [_edge(edge, levels) for edge in area.inner], "across": [_edge(edge, levels) for edge in area.across]}


def assemble(
    graph: GraphAreas,
    layouts: Mapping[str, AreaLayout],
    places: Mapping[str, Place],
    colours: Sequence[str],
) -> VersionMap:
    """
    AI-CORE-BEGIN
    ROLE: Put a version's map together from its areas, their layouts and their places.
    CONTRACT: Every area of ``graph`` needs a place; an area with no layout is listed with ``failed`` and no sketch, so the rest of the map still reads.
    INVARIANTS: Pure; an area's colour follows its order among the areas, and ``colours`` repeats when they run out.
    AI-CORE-END
    """
    levels = {node.id: node.level for area in graph.areas for node in area.nodes}
    overview_areas: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    for index, area in enumerate(graph.areas):
        place = places[area.id]
        counts: dict[str, int] = {}
        for node in area.nodes:
            counts[node.type] = counts.get(node.type, 0) + 1
        item: dict[str, Any] = {"id": area.id, "name": area.name, "colour": colours[index % len(colours)], "x": place.x, "y": place.y, "radius": place.room, "counts": counts}
        layout = layouts.get(area.id)
        if layout is None:
            item["failed"] = True
        else:
            item["sketch"] = _sketch(area, layout, graph.types)
            details[area.id] = _detail(area, layout, place, levels)
        overview_areas.append(item)
    bundles = [[one, other, sum(ends.values()), dict(ends)] for (one, other), ends in sorted(graph.links.items())]
    shared = [{"id": node_id, "domains": list(domains)} for node_id, domains in sorted(graph.memberships.items())]
    return VersionMap({"state": "ready", "types": list(graph.types), "areas": overview_areas, "bundles": bundles, "shared": shared}, details)
