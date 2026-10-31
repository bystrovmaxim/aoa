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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from maxitor.graph_map.areas import Area, GraphAreas, MapEdge
from maxitor.graph_map.layout import AreaLayout
from maxitor.graph_map.places import Place

SKETCH_CELLS = 16
"""How many cells a sketch has across."""

MIN_SKETCH_CELL = 60.0
"""A sketch's cell is never finer than this, in map units."""

STATUSES = ("unchanged", "added", "removed", "changed")
"""What a sketch's status index counts in."""

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


def _glance(graph: GraphAreas, marks: Marks | None) -> dict[str, str]:
    """Each marked node's status, and ``changed`` for what holds a marked node or ends a marked link: what the Changes filter reads."""
    if marks is None:
        return {}
    glance = dict(marks.nodes)
    for area in graph.areas:
        for edge in (*area.inner, *area.across):
            if edge.id in marks.edges:
                glance.setdefault(edge.source, "changed")
                glance.setdefault(edge.target, "changed")
    queue = list(glance)
    while queue:
        for parent in graph.containers.get(queue.pop(), ()):
            if parent not in glance:
                glance[parent] = "changed"
                queue.append(parent)
    return glance


def _sketch(area: Area, layout: AreaLayout, facts: _Facts) -> dict[str, Any]:
    """A coarse grid of the area's nodes: cells are ``[column, row, type index, count, chain index, status index]``, around its centre."""
    cell = max(MIN_SKETCH_CELL, 2 * layout.radius / SKETCH_CELLS)
    counts: dict[tuple[int, int, int, int, int], int] = {}
    for node in area.nodes:
        x, y = layout.positions[node.id]
        key = (int(x // cell), int(y // cell), facts.types.index(node.type), facts.chains[node.above], STATUSES.index(facts.glance.get(node.id, "unchanged")))
        counts[key] = counts.get(key, 0) + 1
    cells = [[column, row, kind, count, chain, status] for (column, row, kind, chain, status), count in sorted(counts.items())]
    return {"cell": round(cell, 1), "cells": cells}


@dataclass(frozen=True, slots=True)
class _Facts:
    """What every part of a map is written with."""

    types: Sequence[str]
    chains: Mapping[tuple[str, ...], int]
    glance: Mapping[str, str]


def _edge(edge: MapEdge, levels: Mapping[str, int], marks: Marks | None) -> dict[str, Any]:
    """One link as an area's detail lists it, with the level from which both its ends show."""
    item: dict[str, Any] = {"id": edge.id, "source": edge.source, "target": edge.target, "type": edge.type, "level": max(levels[edge.source], levels[edge.target])}
    if marks and edge.id in marks.edges:
        item["diff"] = marks.edges[edge.id]
    if marks and edge.id in marks.was:
        item["was"] = marks.was[edge.id]
    return item


def _detail(area: Area, layout: AreaLayout, place: Place, levels: Mapping[str, int], marks: Marks | None, facts: _Facts) -> dict[str, Any]:
    """One area's nodes at their places on the map, and its links."""
    nodes = []
    for node in area.nodes:
        x, y = layout.positions[node.id]
        item: dict[str, Any] = {"id": node.id, "label": node.label, "type": node.type, "level": node.level, "x": round(place.x + x, 1), "y": round(place.y + y, 1)}
        if node.above:
            item["chain"] = facts.chains[node.above]
        if marks and node.id in marks.nodes:
            item["diff"] = marks.nodes[node.id]
        elif node.id in facts.glance:
            item["glance"] = facts.glance[node.id]
        nodes.append(item)
    return {"nodes": nodes, "edges": [_edge(edge, levels, marks) for edge in area.inner], "across": [_edge(edge, levels, marks) for edge in area.across]}


def _changes(graph: GraphAreas, details: Mapping[str, dict[str, Any]], marks: Marks) -> list[dict[str, Any]]:
    """Every changed node and link in the stepping order: domains by size, largest first, then the graph's own order, nodes first."""
    placed = {item["id"]: item for detail in details.values() for item in detail["nodes"]}
    homes = {item["id"]: area_id for area_id, detail in details.items() for item in detail["nodes"]}
    listed: list[dict[str, Any]] = []
    for area in sorted(graph.areas, key=lambda each: (-len(each.nodes), each.id)):
        detail = details.get(area.id, {})
        for item in detail.get("nodes", ()):
            if item["id"] in marks.nodes:
                listed.append({"id": item["id"], "label": item["label"], "area": area.id, "type": item["type"], "status": item["diff"], "x": item["x"], "y": item["y"], "level": item["level"], "ends": [_end(item, area.id)]})
        for link in (*detail.get("edges", ()), *detail.get("across", ())):
            if link["id"] in marks.edges and link["source"] in placed and link["target"] in placed:
                listed.append(_changed_link(link, area.id, placed[link["source"]], placed[link["target"]], homes))
    return listed


def _end(item: Mapping[str, Any], area: str) -> list[Any]:
    """What a filter asks of a node a change stands on: its id, home, type, chain and status."""
    return [item["id"], area, item["type"], item.get("chain", 0), item.get("diff") or item.get("glance") or "unchanged"]


def _changed_link(link: Mapping[str, Any], area: str, start: Mapping[str, Any], end: Mapping[str, Any], homes: Mapping[str, str]) -> dict[str, Any]:
    """A changed link as the steps go to it: at its middle, wide enough to see both its ends."""
    span = round(math.hypot(end["x"] - start["x"], end["y"] - start["y"]), 1)
    middle = {"x": round((start["x"] + end["x"]) / 2, 1), "y": round((start["y"] + end["y"]) / 2, 1)}
    return {"id": link["id"], "label": f"{start['label']} → {end['label']}", "area": area, "type": link["type"], "status": link["diff"], **middle, "level": link["level"], "span": span, "ends": [_end(start, homes[link["source"]]), _end(end, homes[link["target"]])]}


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
    type_colour: Callable[[str], str] = lambda _type: "#64748b",
) -> VersionMap:
    """
    AI-CORE-BEGIN
    ROLE: Put a version's map together from its areas, their layouts and their places.
    CONTRACT: Every area of ``graph`` needs a place; an area with no layout is listed with ``failed`` and no sketch, so the rest of the map still reads.
    INVARIANTS: Pure; an area's colour follows its order among the areas, and ``colours`` repeats when they run out.
    AI-CORE-END
    """
    levels = {node.id: node.level for area in graph.areas for node in area.nodes}
    chains = sorted({node.above for area in graph.areas for node in area.nodes} | {()})
    facts = _Facts(graph.types, {chain: index for index, chain in enumerate(chains)}, _glance(graph, marks))
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
            item["sketch"] = _sketch(area, layout, facts)
            details[area.id] = _detail(area, layout, place, levels, marks, facts)
        if marks:
            _marked(item, area, marks)
        overview_areas.append(item)
    bundles: list[list[Any]] = [[one, other, sum(ends.values()), dict(ends)] for (one, other), ends in sorted(graph.links.items())]
    if marks:
        changed_across = _changed_links(graph, marks)
        for bundle in bundles:
            bundle.append(changed_across.get((bundle[0], bundle[1]), {}))
    shared = [{"id": node_id, "domains": list(domains)} for node_id, domains in sorted(graph.memberships.items())]
    overview: dict[str, Any] = {"state": "ready", "types": list(graph.types), "type_colours": {name: type_colour(name) for name in graph.types}, "chains": [list(chain) for chain in chains], "areas": overview_areas, "bundles": bundles, "shared": shared}
    if marks is None:
        return VersionMap(overview, details)
    drawn = {edge.id for area in graph.areas for edge in (*area.inner, *area.across)}
    overview["links_changed"] = sum(1 for edge_id in marks.edges if edge_id in drawn)
    return VersionMap(overview, details, _changes(graph, details, marks))


def _changed_links(graph: GraphAreas, marks: Marks) -> dict[tuple[str, str], dict[str, int]]:
    """How many links between each pair of areas changed, by status."""
    counted: dict[tuple[str, str], dict[str, int]] = {}
    area_of = {node.id: area.id for area in graph.areas for node in area.nodes}
    for area in graph.areas:
        for edge in area.across:
            if edge.id in marks.edges:
                one, other = area_of[edge.source], area_of[edge.target]
                pair = (min(one, other), max(one, other))
                by_status = counted.setdefault(pair, {})
                by_status[marks.edges[edge.id]] = by_status.get(marks.edges[edge.id], 0) + 1
    return counted
