# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose resource types used by core/diagram actions for ``@connection`` wiring
(see ``LoadGraphAction`` interchange nx graph).
"""

from .networkx_graph_resource import NETWORKX_GRAPH_CONNECTION_KEY, NetworkXGraphResource

__all__ = [
    "NETWORKX_GRAPH_CONNECTION_KEY",
    "NetworkXGraphResource",
]
