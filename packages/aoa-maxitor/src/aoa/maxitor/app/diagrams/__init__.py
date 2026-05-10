# packages/aoa-maxitor/src/aoa/maxitor/app/diagrams/__init__.py
"""
Maxitor ``diagrams`` package — holds :mod:`aoa.maxitor.app.diagrams.graph` (nested folder).

Stable imports may use either this re-export surface or ``aoa.maxitor.app.diagrams.graph`` directly.
"""

from __future__ import annotations

from aoa.maxitor.app.diagrams.graph import (
    G6_CDN_URL,
    HTML_PATH,
    all_axis_graph_node_inspectors,
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
