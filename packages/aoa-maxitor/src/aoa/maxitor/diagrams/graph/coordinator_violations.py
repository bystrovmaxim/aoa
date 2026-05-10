# packages/aoa-maxitor/src/aoa/maxitor/diagrams/graph/coordinator_violations.py
"""
Coordinator DAG cycle keys for graph HTML styling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose :func:`dag_cycle_violation_keys_from_coordinator` without any desktop WebView
coupling (used by the FastAPI diagram routes and interchange G6 export).
"""

from __future__ import annotations

from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


def dag_cycle_violation_keys_from_coordinator(
    coordinator: NodeGraphCoordinator,
) -> set[tuple[str, str, str]]:
    """Match keys used by :func:`interchange_g6_html_string_from_nx` for forbidden-cycle styling."""
    viol = getattr(coordinator, "dag_cycle_violations", ()) or ()
    return {(str(v.source_node_id), str(v.target_node_id), str(v.edge_name)) for v in viol}
