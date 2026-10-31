# packages/maxitor/core/graph_map/src/maxitor/graph_map/layout.py
"""
Layout — the DOT one area is laid out from, and reading what Graphviz answers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each area is laid out on its own with ``sfdp``, ``overlap=scale`` keeping nodes apart. The
DOT lists nodes and links in a fixed order, because ``sfdp`` follows its input: the same
area gives the same positions. This module runs no process; the caller runs ``sfdp
-Tjson0`` on the text and hands the answer back.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Area ──area_dot──► DOT ──(sfdp -Tjson0)──► JSON ──read_layout──► positions, radius
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from maxitor.graph_map.areas import Area

MIN_RADIUS = 150.0
"""An area with little in it still needs room for its name."""

OUTLINE_MARGIN = 170.0
"""How far an area's outline stands from its outermost node."""


@dataclass(frozen=True, slots=True)
class AreaLayout:
    """Positions inside one area, around its centre, and the radius it needs."""

    positions: dict[str, tuple[float, float]]
    radius: float


def area_dot(area: Area) -> str:
    """Write the DOT of one area, in a fixed order."""
    index = {node.id: position for position, node in enumerate(area.nodes)}
    lines = ["digraph G {", "overlap=scale; K=0.55; splines=none;", "node[shape=point,width=.5,height=.5,fixedsize=true];"]
    lines.extend(f"n{position};" for position in range(len(area.nodes)))
    lines.extend(f"n{index[edge.source]}->n{index[edge.target]};" for edge in area.inner)
    lines.append("}")
    return "\n".join(lines)


def read_layout(area: Area, answer: str) -> AreaLayout:
    """Read ``sfdp -Tjson0``'s answer for ``area``: positions around the area's centre."""
    document = json.loads(answer)
    left, bottom, right, top = (float(value) for value in document["bb"].split(","))
    middle_x, middle_y = (left + right) / 2, (bottom + top) / 2
    placed: dict[str, tuple[float, float]] = {}
    for item in document.get("objects", []):
        x, y = (float(value) for value in item["pos"].split(","))
        placed[item["name"]] = (x - middle_x, y - middle_y)
    positions = {node.id: placed[f"n{index}"] for index, node in enumerate(area.nodes)}
    reach = max((math.hypot(x, y) for x, y in positions.values()), default=0.0)
    return AreaLayout(positions, max(MIN_RADIUS, reach) + OUTLINE_MARGIN)
