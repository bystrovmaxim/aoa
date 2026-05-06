# src/maxitor/graph_visualizer/__init__.py
"""
Graph visualizer — :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` **BaseGraphNode** G6 HTML.

Self-contained under :mod:`maxitor.graph_visualizer`.
Use :mod:`maxitor.graph_visualizer.visualizer`.
"""

from __future__ import annotations

from graph.create_node_graph_coordinator import all_axis_graph_node_inspectors
from maxitor.graph_visualizer.visualizer import (
    G6_CDN_URL,
    INTERCHANGE_AXES_GRAPH_HTML_PATH,
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
