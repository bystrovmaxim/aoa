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
            └── (visualizer) export_samples_graph_html  →  archive/logs/*.html (live coordinator graph)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``build_sample_coordinator`` mirrors ``CoreActionMachine.create_coordinator`` inspector
  registration for reproducible graph fixtures.
- Graph exports prefer ``get_graph()`` when present so HTML and GraphML stay
  aligned on the interchange view.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- **Happy path:** ``from maxitor import build_sample_coordinator`` then
  ``coord = build_sample_coordinator()`` for graph and snapshot reads.
- **Edge case:** ``from maxitor import export_samples_graph_graphml`` writes
  GraphML without importing the HTML stack.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Export helpers perform I/O under ``archive/logs``; callers must have write access
  to the repository tree when using default paths.

AI-CORE-BEGIN
ROLE: Public entry point for the ActionMachine samples graph harness.
EXPORTS: ``StoreDomain``, ``build_sample_coordinator``, ``export_samples_graph_graphml``.
ENTRY PATTERN: ``from maxitor import build_sample_coordinator`` then ``coord = build_sample_coordinator()``;
GraphML: ``from maxitor import export_samples_graph_graphml``.
INTERNAL FLOW: ``maxitor.samples`` registers decorators → ``CoreActionMachine.create_coordinator``.
AI-CORE-END
"""

from __future__ import annotations

from maxitor.graph_export import export_samples_graph_graphml
from maxitor.samples.build import build_sample_coordinator
from maxitor.samples.store.domain import StoreDomain

__all__ = [
    "StoreDomain",
    "build_sample_coordinator",
    "export_samples_graph_graphml",
]
