# packages/aoa-maxitor/src/aoa/maxitor/diagrams/graph/__init__.py
"""
Interchange graph G6 exporter — HTML for :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`.

Use :mod:`aoa.maxitor.diagrams.graph.html_page`; ``dag_cycle_violation_keys_from_coordinator``
lives in :mod:`aoa.maxitor.diagrams.graph.coordinator_violations`.
"""

from __future__ import annotations

from aoa.action_machine.graph_model.node_graph_coordinator_factory import all_axis_graph_node_inspectors

from .coordinator_violations import dag_cycle_violation_keys_from_coordinator
from .html_page import (
    G6_CDN_URL,
    interchange_g6_html_string_from_coordinator,
    interchange_g6_html_string_from_nx,
)

__all__ = [
    "G6_CDN_URL",
    "all_axis_graph_node_inspectors",
    "dag_cycle_violation_keys_from_coordinator",
    "interchange_g6_html_string_from_coordinator",
    "interchange_g6_html_string_from_nx",
]
