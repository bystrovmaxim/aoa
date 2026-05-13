# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose resource types used by core/diagram actions for ``@connection`` wiring
(see ``LoadGraphAction`` interchange nx graph).
"""

from .duckdb_graph_resource import (
    DEFAULT_EXAMPLE_GRAPH_JSON_URL,
    DUCKDB_GRAPH_CONNECTION_KEY,
    ENV_EXAMPLE_GRAPH_JSON_URL,
    DuckDBGraphResource,
)
from .networkx_graph_resource import NETWORKX_GRAPH_CONNECTION_KEY, NetworkXGraphResource

__all__ = [
    "DEFAULT_EXAMPLE_GRAPH_JSON_URL",
    "DUCKDB_GRAPH_CONNECTION_KEY",
    "ENV_EXAMPLE_GRAPH_JSON_URL",
    "NETWORKX_GRAPH_CONNECTION_KEY",
    "DuckDBGraphResource",
    "NetworkXGraphResource",
]
