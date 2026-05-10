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
import json
from pathlib import Path

from aoa.action_machine.graph_model.node_graph_coordinator_factory import all_axis_graph_node_inspectors
from aoa.graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.app_view.actions.build_interchange_graph_data_action import (
    interchange_g6_payload_from_coordinator,
)
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
    """Build the sample node graph and write the interchange graph JSON export."""
    out = Path.cwd() / "archive" / "logs" / "samples_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = interchange_g6_payload_from_coordinator(build_sample_node_graph_coordinator(), title=title)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
