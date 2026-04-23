# src/maxitor/viz2/__init__.py
"""
Viz2 — :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` **BaseGraphNode** G6 HTML.

Self-contained under :mod:`maxitor.viz2` (no imports from :mod:`maxitor.viz1`).
Use :mod:`maxitor.viz2.interchange_graph_visualizer`.
"""

from __future__ import annotations

from maxitor.viz2.interchange_graph_visualizer import (
    G6_CDN_URL,
    INTERCHANGE_AXES_GRAPH_HTML_PATH,
    all_axis_graph_node_inspectors,
    export_interchange_axes_graph_html,
    generate_interchange_g6_html,
)

__all__ = [
    "G6_CDN_URL",
    "INTERCHANGE_AXES_GRAPH_HTML_PATH",
    "all_axis_graph_node_inspectors",
    "export_interchange_axes_graph_html",
    "generate_interchange_g6_html",
]
