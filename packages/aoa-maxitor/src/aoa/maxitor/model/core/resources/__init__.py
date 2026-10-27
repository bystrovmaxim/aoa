# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the resources core actions use for ``@connection`` wiring: the gateway that
downloads a ``graph-json``, the controller over the store of built graphs, and the
installed client bundle.
"""

from .graph_source_gateway import (
    FETCH_TIMEOUT_SECONDS,
    GRAPH_SOURCE_CONNECTION_KEY,
    Document,
    GraphSourceGateway,
    Unreachable,
)
from .graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from .static_bundle_resource import STATIC_BUNDLE_CONNECTION_KEY, StaticBundleResource

__all__ = [
    "FETCH_TIMEOUT_SECONDS",
    "GRAPH_SOURCE_CONNECTION_KEY",
    "GRAPH_STORE_CONNECTION_KEY",
    "STATIC_BUNDLE_CONNECTION_KEY",
    "Document",
    "GraphSourceGateway",
    "GraphStoreController",
    "StaticBundleResource",
    "Unreachable",
]
