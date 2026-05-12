# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose resource types used by core/diagram actions for ``@connection`` wiring
(see ``LoadGraphAction`` interchange nx graph). Both resources use the same connection key
``SERVICE_GRAPH_CONNECTION_KEY`` from :mod:`aoa.maxitor.model.core.resources.service_graph_resource`.
"""

from .networkx_graph_resource import NetworkXGraphResource
from .service_graph_resource import SERVICE_GRAPH_CONNECTION_KEY, ServiceGraphResource

__all__ = [
    "SERVICE_GRAPH_CONNECTION_KEY",
    "NetworkXGraphResource",
    "ServiceGraphResource",
]
