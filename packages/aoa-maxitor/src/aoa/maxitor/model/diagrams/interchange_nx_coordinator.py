# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/interchange_nx_coordinator.py
"""
interchange_nx_coordinator — recover ``NodeGraphCoordinator`` from a Maxitor nx graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``LoadGraphAction`` embeds the built coordinator under ``MAXITOR_NX_GRAPH_COORDINATOR_KEY``
on the NetworkX ``graph`` mapping. Diagram actions that read ``ServiceGraphResource.service``
reuse this helper instead of duplicating lookup logic.
"""

from __future__ import annotations

from typing import Any

from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.core.actions.load_graph_action import MAXITOR_NX_GRAPH_COORDINATOR_KEY


def node_graph_coordinator_from_interchange_nx(nx_graph: Any) -> NodeGraphCoordinator:
    """Recover the coordinator embedded by :class:`~aoa.maxitor.model.core.actions.load_graph_action.LoadGraphAction`."""
    gdict = getattr(nx_graph, "graph", None)
    if not isinstance(gdict, dict):
        msg = "nx_graph must be a NetworkX graph with a mapping ``graph`` attribute."
        raise TypeError(msg)
    coordinator = gdict.get(MAXITOR_NX_GRAPH_COORDINATOR_KEY)
    if coordinator is None:
        msg = (
            f"Interchange nx_graph is missing coordinator under {MAXITOR_NX_GRAPH_COORDINATOR_KEY!r}; "
            "materialize it with LoadGraphAction.Params(graph=coordinator) first."
        )
        raise ValueError(msg)
    if not isinstance(coordinator, NodeGraphCoordinator):
        msg = (
            f"Expected {MAXITOR_NX_GRAPH_COORDINATOR_KEY!r} to hold a NodeGraphCoordinator, "
            f"got {type(coordinator).__name__}."
        )
        raise TypeError(msg)
    return coordinator
