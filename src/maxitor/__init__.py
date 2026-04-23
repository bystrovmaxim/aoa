# src/maxitor/__init__.py
"""
Maxitor — sample graph helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a minimal harness around :mod:`maxitor.samples`: one import path to the
primary domain marker, the legacy sample coordinator builder still used by graph
contract tests, and the new viz2 HTML export path built on
``NodeGraphCoordinator``.
"""

from __future__ import annotations

from maxitor.samples.build import build_sample_coordinator
from maxitor.samples.node_build import (
    build_sample_node_graph_coordinator,
    export_samples_graph_html,
)
from maxitor.samples.store.domain import StoreDomain

__all__ = [
    "StoreDomain",
    "build_sample_coordinator",
    "build_sample_node_graph_coordinator",
    "export_samples_graph_html",
]
