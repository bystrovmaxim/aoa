# src/action_machine/interchange_vertex_labels.py
"""
Interchange / facet kind strings (``node_type``) for graph visualization labels.

Kept dependency-free so modules like ``maxitor.visualizer`` can import without
pulling ``action_machine.dependencies`` (whose package ``__init__`` loads the
factory graph) or ``action_machine.graph`` (whose package ``__init__`` loads the
coordinator).
"""

from __future__ import annotations

from typing import Final

# Structural ``BaseAction`` primary vertex (depends / connection / facets merged here).
ACTION_VERTEX_TYPE: Final[str] = "Action"

# Class-dependency stubs from ``DependencyIntentInspector`` (non-``BaseAction`` @depends).
SERVICE_VERTEX_TYPE: Final[str] = "Service"
