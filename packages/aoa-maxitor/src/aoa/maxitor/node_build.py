# packages/aoa-maxitor/src/aoa/maxitor/node_build.py
"""
Sample NodeGraphCoordinator builder and JSON export helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Bridge sample model registration modules (see
:data:`aoa.maxitor.interchange_demo_coordinator.SAMPLE_MODEL_REGISTRATION_MODULE_NAMES`)
to :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator` and write the
raw interchange JSON export used by tooling.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from aoa.action_machine.graph.core.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.node_graph_coordinator_factory import GRAPH_JSON_SCHEMA, all_axis_graph_node_inspectors
from aoa.maxitor.interchange_demo_coordinator import SAMPLE_MODEL_REGISTRATION_MODULE_NAMES


def build_sample_node_graph_coordinator() -> NodeGraphCoordinator:
    """Import example modules and build a debug graph coordinator for Maxitor inspection."""
    for name in SAMPLE_MODEL_REGISTRATION_MODULE_NAMES:
        importlib.import_module(name)
    coordinator = DebugNodeGraphCoordinator()
    coordinator.build(all_axis_graph_node_inspectors(), export_json_schema=GRAPH_JSON_SCHEMA)
    return coordinator


def export_samples_graph_html(
    *,
    title: str = "ActionMachine · interchange axes",
) -> Path:
    """Build the sample node graph and write the raw interchange graph JSON export."""
    out = Path.cwd() / "archive" / "logs" / "samples_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _ = title
    payload = json.loads(build_sample_node_graph_coordinator().to_json())
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
