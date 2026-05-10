# packages/aoa-maxitor/src/aoa/maxitor/samples/node_build.py
"""
Sample NodeGraphCoordinator builder and HTML export helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small bridge from ``aoa.maxitor.samples`` imports to the new
``NodeGraphCoordinator``-based visualization flow. This keeps sample HTML export
on the new graph stack while the runtime still transitions away from the legacy
coordinator.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from aoa.action_machine.graph_model.node_graph_coordinator_factory import all_axis_graph_node_inspectors
from aoa.graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.diagrams.graph.html_page import interchange_g6_html_string_from_coordinator
from aoa.maxitor.samples.build import _MODULES


def build_sample_node_graph_coordinator() -> NodeGraphCoordinator:
    """Import sample modules and build a debug graph coordinator for Maxitor inspection."""
    for name in _MODULES:
        importlib.import_module(name)
    coordinator = DebugNodeGraphCoordinator()
    coordinator.build(all_axis_graph_node_inspectors())
    return coordinator


def export_samples_graph_html(
    *,
    title: str = "ActionMachine · interchange axes",
) -> Path:
    """Build the sample node graph and write the graph visualizer HTML export."""
    out = Path.cwd() / "archive" / "logs" / "samples_graph.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        interchange_g6_html_string_from_coordinator(build_sample_node_graph_coordinator(), title=title),
        encoding="utf-8",
    )
    return out
