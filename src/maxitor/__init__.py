# src/maxitor/__init__.py
"""
Maxitor — purpose.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a **minimal harness** around :mod:`maxitor.samples` for ActionMachine:
one import path to the primary domain marker, a coordinator factory, and optional **GraphML**
export helpers. The package avoids pulling ``archive`` or a separate ``graph_domain``
tree into normal imports.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    maxitor.samples (store, billing, messaging, catalog, roles)
            │
            ▼
    build_sample_coordinator()  →  GraphCoordinator (built)
            │
            ├── export_samples_graph_graphml  →  archive/logs/*.graphml
            └── (:mod:`maxitor.viz1.visualizer`) ``export_samples_graph_html``  →  archive/logs/*.html

"""

from __future__ import annotations

from maxitor.samples.build import build_sample_coordinator
from maxitor.samples.store.domain import StoreDomain
from maxitor.viz1.graph_export import export_samples_graph_graphml

__all__ = [
    "StoreDomain",
    "build_sample_coordinator",
    "export_samples_graph_graphml",
]
