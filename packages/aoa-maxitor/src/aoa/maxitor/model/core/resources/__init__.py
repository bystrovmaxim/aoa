# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose resource types used by core/diagram actions for ``@connection`` wiring
(see ``LoadGraphAction`` interchange nx graph).
"""

from .service_graph_resource import SERVICE_GRAPH_CONNECTION_KEY, ServiceGraphResource

__all__ = [
    "SERVICE_GRAPH_CONNECTION_KEY",
    "ServiceGraphResource",
]
