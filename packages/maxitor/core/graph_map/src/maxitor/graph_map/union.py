# packages/maxitor/core/graph_map/src/maxitor/graph_map/union.py
"""
Union — the map of two versions: everything in A or B, at B's positions, marked.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two versions are read as one map (spec 040, FR-020, FR-021). Nodes stand where they stand
in B, so switching One to Diff moves nothing. A node only in A takes its place from A, and
steps aside when that place is taken. A relation that points elsewhere now stays one link,
remembering its target in A. The statuses come from the comparison; this module only places
what it is told about.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    document A + document B ──union_document──► one document, B winning
    layouts of A and of B ──union_layouts──► positions for every area of the union
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from maxitor.graph_map.areas import Area, GraphAreas
from maxitor.graph_map.layout import OUTLINE_MARGIN, AreaLayout

STEP_ASIDE = 45.0
"""How far apart a node only in A stands from what is already there."""

GOLDEN_ANGLE = 2.399963229728653


def union_document(older: Mapping[str, Any], newer: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Every node and link of either version, B's winning, and each link's target in A where it differs."""
    nodes = {node["id"]: node for node in older.get("nodes", [])} | {node["id"]: node for node in newer.get("nodes", [])}
    before = {edge["id"]: edge for edge in older.get("edges", [])}
    edges = before | {edge["id"]: edge for edge in newer.get("edges", [])}
    retargeted = {edge["id"]: before[edge["id"]]["target_id"] for edge in newer.get("edges", []) if edge["id"] in before and before[edge["id"]]["target_id"] != edge["target_id"]}
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}, retargeted


def _beside(wanted: tuple[float, float], taken: list[tuple[float, float]]) -> tuple[float, float]:
    """The nearest spot to ``wanted`` that stands clear of what is taken."""
    step = 0
    while True:
        distance = STEP_ASIDE * math.sqrt(step)
        x, y = wanted[0] + distance * math.cos(step * GOLDEN_ANGLE), wanted[1] + distance * math.sin(step * GOLDEN_ANGLE)
        if all(math.hypot(x - other[0], y - other[1]) >= STEP_ASIDE for other in taken):
            return x, y
        step += 1


def _merged(area: Area, newer: AreaLayout | None, older: AreaLayout | None) -> AreaLayout | None:
    """One area's positions: B's, then each node only in A at A's place or beside it."""
    base = newer or older
    if base is None:
        return None
    positions: dict[str, tuple[float, float]] = {}
    for node in area.nodes:
        if node.id in base.positions:
            positions[node.id] = base.positions[node.id]
    taken = list(positions.values())
    for node in area.nodes:
        if node.id not in positions:
            wanted = older.positions.get(node.id, (0.0, 0.0)) if older else (0.0, 0.0)
            positions[node.id] = _beside(wanted, taken)
            taken.append(positions[node.id])
    reach = max(math.hypot(x, y) for x, y in positions.values())
    return AreaLayout(positions, max(base.radius, reach + OUTLINE_MARGIN))


def union_layouts(union: GraphAreas, older: Mapping[str, AreaLayout], newer: Mapping[str, AreaLayout]) -> dict[str, AreaLayout]:
    """
    AI-CORE-BEGIN
    ROLE: Give every area of the union its positions, from the layouts of both versions.
    CONTRACT: A node in B stands exactly where B has it; a node only in A at A's place, or the nearest spot clear of the rest.
    INVARIANTS: Pure; an area with no layout in either version is left out, so it reads as failed.
    AI-CORE-END
    """
    merged = {area.id: _merged(area, newer.get(area.id), older.get(area.id)) for area in union.areas}
    return {area_id: layout for area_id, layout in merged.items() if layout is not None}
