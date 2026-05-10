# packages/aoa-maxitor/src/aoa/maxitor/app/diagrams/graph/__init__.py
"""
Graph visualizer — :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator` **BaseGraphNode** G6 HTML.

Self-contained under :mod:`aoa.maxitor.app.diagrams.graph`.
Use :mod:`aoa.maxitor.app.diagrams.graph.component`.
"""

from __future__ import annotations

from aoa.action_machine.graph_model.node_graph_coordinator_factory import all_axis_graph_node_inspectors

from .component import (
    G6_CDN_URL,
    HTML_PATH,
    export_interchange_axes_graph_html,
    generate_interchange_g6_html,
)

__all__ = [
    "G6_CDN_URL",
    "HTML_PATH",
    "all_axis_graph_node_inspectors",
    "export_interchange_axes_graph_html",
    "generate_interchange_g6_html",
]
