# packages/maxitor/core/graph_map/src/maxitor/graph_map/__init__.py
"""
graph_map — a graph of the Open Gnomon Protocol as a map.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The full graph of a large system cannot reach a browser whole, so it is cut into areas,
one per domain, each laid out on its own, and read in parts: an overview first, one area
at a time after it. This package holds the part that needs only the graph document; it
imports nothing of AOA, the app or a tool, and runs no process.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    document ──split_areas──► areas ──area_dot──► (the caller runs sfdp) ──read_layout──► AreaLayout
                                │                                                            │
                                └───────────── settle_places ◄───────── radii ◄──────────────┘
                                                     │
                                                     ▼
                                     assemble ──► overview, each area's detail
"""

from maxitor.graph_map.areas import OUTSIDE, Area, GraphAreas, MapNode, split_areas
from maxitor.graph_map.assemble import VersionMap, assemble
from maxitor.graph_map.layout import AreaLayout, area_dot, read_layout
from maxitor.graph_map.places import Place, settle_places

__all__ = [
    "OUTSIDE",
    "Area",
    "AreaLayout",
    "GraphAreas",
    "MapNode",
    "Place",
    "VersionMap",
    "area_dot",
    "assemble",
    "read_layout",
    "settle_places",
    "split_areas",
]
