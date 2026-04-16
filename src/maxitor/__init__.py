# src/maxitor/__init__.py
"""
Maxitor — purpose.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a **minimal harness** around the synthetic ``test_domain`` for ActionMachine:
one import path to the domain marker, a coordinator factory, and optional **GraphML**
export helpers. The package avoids pulling ``archive`` or a separate ``graph_domain``
tree into normal imports.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    maxitor.test_domain (decorators, actions, entities, …)
            │
            ▼
    build_test_coordinator()  →  GateCoordinator (built)
            │
            ├── export_test_domain_graph_graphml  →  archive/logs/*.graphml
            └── (visualizer) export_test_domain_graph_html  →  archive/logs/*.html

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``build_test_coordinator`` mirrors ``CoreActionMachine.create_coordinator`` inspector
  registration for reproducible graph fixtures.
- Graph exports prefer ``get_logical_graph()`` when present so HTML and GraphML stay
  aligned on the interchange view.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- **Happy path:** ``from maxitor import build_test_coordinator`` then
  ``coord = build_test_coordinator()`` for graph and snapshot reads.
- **Edge case:** ``from maxitor import export_test_domain_graph_graphml`` writes
  GraphML without importing the HTML stack.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Export helpers perform I/O under ``archive/logs``; callers must have write access
  to the repository tree when using default paths.

AI-CORE-BEGIN
ROLE: Public entry point for the ActionMachine test-domain graph harness.
EXPORTS: ``TestDomain``, ``build_test_coordinator``, ``export_test_domain_graph_graphml``.
ENTRY PATTERN: ``from maxitor import build_test_coordinator`` then ``coord = build_test_coordinator()``;
GraphML: ``from maxitor import export_test_domain_graph_graphml``.
INTERNAL FLOW: ``test_domain`` registers decorators → ``CoreActionMachine.create_coordinator``.
AI-CORE-END
"""

from __future__ import annotations

from maxitor.graph_export import export_test_domain_graph_graphml
from maxitor.test_domain.build import build_test_coordinator
from maxitor.test_domain.domain import TestDomain

__all__ = [
    "TestDomain",
    "build_test_coordinator",
    "export_test_domain_graph_graphml",
]
