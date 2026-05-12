# packages/aoa-maxitor/src/aoa/maxitor/node_build.py
"""
Sample NodeGraphCoordinator builder and HTML export helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Bridge sample model registration modules (see :data:`aoa.maxitor.interchange_demo_coordinator.SAMPLE_MODEL_REGISTRATION_MODULE_NAMES`) to :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`
and to Maxitor interchange G6 payload helpers. Lives in Maxitor because export uses
:class:`~aoa.maxitor.model.diagrams.actions.build_interchange_graph_data_action`.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from aoa.action_machine.graph_model.node_graph_coordinator_factory import (
    GRAPH_JSON_SCHEMA,
    all_axis_graph_node_inspectors,
)
from aoa.graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.interchange_demo_coordinator import SAMPLE_MODEL_REGISTRATION_MODULE_NAMES
from aoa.maxitor.model.diagrams.actions.build_interchange_graph_data_action import (
    interchange_g6_payload_from_coordinator,
)


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
    """Build the sample node graph and write the interchange graph JSON export."""
    out = Path.cwd() / "archive" / "logs" / "samples_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = interchange_g6_payload_from_coordinator(build_sample_node_graph_coordinator(), title=title)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
