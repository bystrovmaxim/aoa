# packages/aoa-maxitor/src/aoa/maxitor/__init__.py
"""
Maxitor — sample graph helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a minimal harness around :mod:`aoa.maxitor.samples`: one import path to the
primary domain marker and the graph visualizer HTML export path built on
``NodeGraphCoordinator``.
"""

from __future__ import annotations

from aoa.maxitor.samples.node_build import (
    build_sample_node_graph_coordinator,
    export_samples_graph_html,
)
from aoa.maxitor.samples.store.domain import StoreDomain

__all__ = [
    "StoreDomain",
    "build_sample_node_graph_coordinator",
    "export_samples_graph_html",
]
