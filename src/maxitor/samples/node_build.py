# src/maxitor/samples/node_build.py
"""
Sample NodeGraphCoordinator builder and HTML export helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small bridge from ``maxitor.samples`` imports to the new
``NodeGraphCoordinator``-based visualization flow. This keeps sample HTML export
on the new graph stack while the runtime still transitions away from the legacy
coordinator.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from graph.create_node_graph_coordinator import all_axis_graph_node_inspectors
from graph.node_graph_coordinator import NodeGraphCoordinator
from maxitor.samples.build import _MODULES
from maxitor.viz2.interchange_graph_visualizer import export_interchange_axes_graph_html


def build_sample_node_graph_coordinator() -> NodeGraphCoordinator:
    """Import sample modules and build a ``NodeGraphCoordinator`` for them."""
    for name in _MODULES:
        importlib.import_module(name)
    coordinator = NodeGraphCoordinator()
    coordinator.build(all_axis_graph_node_inspectors())
    return coordinator


def export_samples_graph_html(
    *,
    title: str = "ActionMachine · interchange axes",
) -> Path:
    """Build the sample node graph and write the viz2 HTML export."""
    return export_interchange_axes_graph_html(
        build_sample_node_graph_coordinator(),
        title=title,
    )
