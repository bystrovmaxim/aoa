# packages/aoa-maxitor/src/aoa/maxitor/diagrams/__init__.py
"""
Maxitor diagrams — interchange graph HTML for the FastAPI backend and ERD data helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Re-export the graph HTML helpers for stable ``from aoa.maxitor.diagrams import …`` imports;
subpackages expose :mod:`aoa.maxitor.diagrams.graph` and :mod:`aoa.maxitor.diagrams.erd`.
"""

from __future__ import annotations

from aoa.maxitor.diagrams.graph import (
    G6_CDN_URL,
    all_axis_graph_node_inspectors,
    interchange_g6_html_string_from_coordinator,
    interchange_g6_html_string_from_nx,
)

__all__ = [
    "G6_CDN_URL",
    "all_axis_graph_node_inspectors",
    "interchange_g6_html_string_from_coordinator",
    "interchange_g6_html_string_from_nx",
]
