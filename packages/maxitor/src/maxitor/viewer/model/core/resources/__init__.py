# packages/maxitor/src/maxitor/viewer/model/core/resources/__init__.py
"""
Maxitor core — ActionMachine connection resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the resources core actions use for ``@connection`` wiring: the gateway that
downloads a ``graph-json``, the controller over the store of built graphs, the tabs
outside rooms, the clock that keeps held graphs fresh, and the installed client bundle.
"""

from .graph_source_gateway import (
    FETCH_TIMEOUT_SECONDS,
    GRAPH_SOURCE_CONNECTION_KEY,
    Document,
    GraphSourceGateway,
    NotModified,
    Unreachable,
)
from .graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from .open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from .source_checks import SOURCE_CHECKS_CONNECTION_KEY, SourceChecks
from .static_bundle_resource import STATIC_BUNDLE_CONNECTION_KEY, StaticBundleResource

__all__ = [
    "FETCH_TIMEOUT_SECONDS",
    "GRAPH_SOURCE_CONNECTION_KEY",
    "GRAPH_STORE_CONNECTION_KEY",
    "OPEN_TABS_CONNECTION_KEY",
    "SOURCE_CHECKS_CONNECTION_KEY",
    "STATIC_BUNDLE_CONNECTION_KEY",
    "Document",
    "GraphSourceGateway",
    "GraphStoreController",
    "NotModified",
    "OpenTabsRegistry",
    "SourceChecks",
    "StaticBundleResource",
    "Unreachable",
]
