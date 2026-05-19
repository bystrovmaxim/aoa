# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/__init__.py
"""
Maxitor diagrams — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose resource types used by diagram actions for ``@connection`` wiring.
"""

from .duckdb_graph_resource import (
    DEFAULT_EXAMPLE_GRAPH_JSON_URL,
    DUCKDB_GRAPH_CONNECTION_KEY,
    ENV_EXAMPLE_GRAPH_JSON_URL,
    DuckDBGraphResource,
)

__all__ = [
    "DEFAULT_EXAMPLE_GRAPH_JSON_URL",
    "DUCKDB_GRAPH_CONNECTION_KEY",
    "ENV_EXAMPLE_GRAPH_JSON_URL",
    "DuckDBGraphResource",
]
