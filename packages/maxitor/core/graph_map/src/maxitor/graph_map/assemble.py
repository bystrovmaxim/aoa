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

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from maxitor.graph_map.areas import Area, GraphAreas, MapEdge
from maxitor.graph_map.layout import AreaLayout
from maxitor.graph_map.places import Place

SKETCH_CELLS = 16
"""How many cells a sketch has across."""

MIN_SKETCH_CELL = 60.0
"""A sketch's cell is never finer than this, in map units."""

WHOLE_AREA_STATUSES = frozenset({"added", "removed"})
"""What a comparison can say of a domain as a whole; a changed domain is said by its count."""


@dataclass(frozen=True, slots=True)
class VersionMap:
    """What a version's map is read from; ``changes`` lists a pair's changed nodes in the stepping order."""

    overview: dict[str, Any]
    details: dict[str, dict[str, Any]]
    changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Marks:
    """What a comparison says of a pair: only what changed is named."""

    nodes: Mapping[str, str]
    edges: Mapping[str, str]
    was: Mapping[str, str]


def _sketch(area: Area, layout: AreaLayout, types: Sequence[str]) -> dict[str, Any]:
    """A coarse grid of the area's nodes by type: cells are ``[column, row, type index, count]``, around its centre."""
    cell = max(MIN_SKETCH_CELL, 2 * layout.radius / SKETCH_CELLS)
    counts: dict[tuple[int, int, int], int] = {}
    for node in area.nodes:
        x, y = layout.positions[node.id]
        key = (int(x // cell), int(y // cell), types.index(node.type))
        counts[key] = counts.get(key, 0) + 1
    return {"cell": round(cell, 1), "cells": [[*key, count] for key, count in sorted(counts.items())]}


def _edge(edge: MapEdge, levels: Mapping[str, int], marks: Marks | None) -> dict[str, Any]:
    """One link as an area's detail lists it, with the level from which both its ends show."""
    item: dict[str, Any] = {"id": edge.id, "source": edge.source, "target": edge.target, "type": edge.type, "level": max(levels[edge.source], levels[edge.target])}
    if marks and edge.id in marks.edges:
        item["diff"] = marks.edges[edge.id]
    if marks and edge.id in marks.was:
        item["was"] = marks.was[edge.id]
    return item


def _detail(area: Area, layout: AreaLayout, place: Place, levels: Mapping[str, int], marks: Marks | None) -> dict[str, Any]:
    """One area's nodes at their places on the map, and its links."""
    nodes = []
    for node in area.nodes:
        x, y = layout.positions[node.id]
        item: dict[str, Any] = {"id": node.id, "label": node.label, "type": node.type, "level": node.level, "x": round(place.x + x, 1), "y": round(place.y + y, 1)}
        if marks and node.id in marks.nodes:
            item["diff"] = marks.nodes[node.id]
        nodes.append(item)
    return {"nodes": nodes, "edges": [_edge(edge, levels, marks) for edge in area.inner], "across": [_edge(edge, levels, marks) for edge in area.across]}


def _changes(graph: GraphAreas, details: Mapping[str, dict[str, Any]], marks: Marks) -> list[dict[str, Any]]:
    """Every changed node and link in the stepping order: domains by size, largest first, then the graph's own order, nodes first."""
    placed = {item["id"]: item for detail in details.values() for item in detail["nodes"]}
    listed: list[dict[str, Any]] = []
    for area in sorted(graph.areas, key=lambda each: (-len(each.nodes), each.id)):
        detail = details.get(area.id, {})
        for item in detail.get("nodes", ()):
            if item["id"] in marks.nodes:
                listed.append({"id": item["id"], "label": item["label"], "area": area.id, "type": item["type"], "status": item["diff"], "x": item["x"], "y": item["y"], "level": item["level"]})
        for link in (*detail.get("edges", ()), *detail.get("across", ())):
            if link["id"] in marks.edges and link["source"] in placed and link["target"] in placed:
                listed.append(_changed_link(link, area.id, placed[link["source"]], placed[link["target"]]))
    return listed


def _changed_link(link: Mapping[str, Any], area: str, start: Mapping[str, Any], end: Mapping[str, Any]) -> dict[str, Any]:
    """A changed link as the steps go to it: at its middle, wide enough to see both its ends."""
    span = round(math.hypot(end["x"] - start["x"], end["y"] - start["y"]), 1)
    middle = {"x": round((start["x"] + end["x"]) / 2, 1), "y": round((start["y"] + end["y"]) / 2, 1)}
    return {"id": link["id"], "label": f"{start['label']} → {end['label']}", "area": area, "type": link["type"], "status": link["diff"], **middle, "level": link["level"], "span": span}


def _marked(item: dict[str, Any], area: Area, marks: Marks) -> None:
    """Add what a comparison says of a whole area to its overview entry."""
    changes: dict[str, dict[str, int]] = {}
    for node in area.nodes:
        status = marks.nodes.get(node.id)
        if status:
            by_type = changes.setdefault(node.type, {})
            by_type[status] = by_type.get(status, 0) + 1
    item["changes"] = changes
    if marks.nodes.get(area.id) in WHOLE_AREA_STATUSES:
        item["status"] = marks.nodes[area.id]


def assemble(
    graph: GraphAreas,
    layouts: Mapping[str, AreaLayout],
    places: Mapping[str, Place],
    colours: Sequence[str],
    marks: Marks | None = None,
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
            details[area.id] = _detail(area, layout, place, levels, marks)
        if marks:
            _marked(item, area, marks)
        overview_areas.append(item)
    bundles: list[list[Any]] = [[one, other, sum(ends.values()), dict(ends)] for (one, other), ends in sorted(graph.links.items())]
    if marks:
        changed_across = _changed_links(graph, marks)
        for bundle in bundles:
            bundle.append(changed_across.get((bundle[0], bundle[1]), 0))
    shared = [{"id": node_id, "domains": list(domains)} for node_id, domains in sorted(graph.memberships.items())]
    overview: dict[str, Any] = {"state": "ready", "types": list(graph.types), "areas": overview_areas, "bundles": bundles, "shared": shared}
    if marks is None:
        return VersionMap(overview, details)
    drawn = {edge.id for area in graph.areas for edge in (*area.inner, *area.across)}
    overview["links_changed"] = sum(1 for edge_id in marks.edges if edge_id in drawn)
    return VersionMap(overview, details, _changes(graph, details, marks))


def _changed_links(graph: GraphAreas, marks: Marks) -> dict[tuple[str, str], int]:
    """How many links between each pair of areas changed."""
    counted: dict[tuple[str, str], int] = {}
    area_of = {node.id: area.id for area in graph.areas for node in area.nodes}
    for area in graph.areas:
        for edge in area.across:
            if edge.id in marks.edges:
                one, other = area_of[edge.source], area_of[edge.target]
                pair = (min(one, other), max(one, other))
                counted[pair] = counted.get(pair, 0) + 1
    return counted
