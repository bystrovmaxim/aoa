# src/action_machine/interchange_vertex_labels.py
"""
Interchange ``vertex_type`` / facet ``node_type`` string labels.

Kept dependency-free so modules like ``maxitor.visualizer`` can import without
pulling ``action_machine.dependencies`` (whose package ``__init__`` loads the
factory graph) or ``action_machine.graph`` (whose package ``__init__`` loads the
coordinator).
"""

from __future__ import annotations

from typing import Final

# Class dependency stubs from ``DependencyIntentInspector`` (non-``BaseAction`` @depends).
DEPENDENCY_SERVICE_VERTEX_TYPE: Final[str] = "DependencyService"
