# src/action_machine/graph/logical/__init__.py

"""
Logical graph types and the **G0** minimal synthetic builder (golden ``logical_minimal.json``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose immutable ``LogicalVertex`` / ``LogicalEdge`` models, **PR1** constants and
id/reverse helpers, plus ``build_from_g0_input`` (**G0**, landed before PR2 in the repo).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    tests/fixtures/golden_graph/logical_minimal.json
              │
              ▼
    build_from_g0_input(bundle["input"])
              │
              ▼
    vertices + edges  →  canonical compare

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- G0 builder is deterministic for a valid input document.
- Full coordinator integration lives in later PRs; this package stays side-effect free.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- ``from action_machine.graph.logical import build_from_g0_input, LogicalVertex``

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``build_from_g0_input`` covers only the G0 synthetic schema, not real facet payloads.
"""

from __future__ import annotations

from action_machine.graph.logical.constants import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
    REVERSE_EDGE_MAP,
    REVERSE_EDGE_STEREOTYPE,
    VERTEX_TYPES,
)
from action_machine.graph.logical.g0_builder import build_from_g0_input
from action_machine.graph.logical.model import LogicalEdge, LogicalVertex
from action_machine.graph.logical.reverse_edge import reverse_direct_edge
from action_machine.graph.logical.vertex_id import (
    split_checker_vertex_id,
    split_host_element_vertex_id,
)

__all__ = [
    "DAG_EDGE_TYPES",
    "INTERNAL_EDGE_TYPES",
    "OWNERSHIP_EDGE_TYPES",
    "REVERSE_EDGE_MAP",
    "REVERSE_EDGE_STEREOTYPE",
    "VERTEX_TYPES",
    "LogicalEdge",
    "LogicalVertex",
    "build_from_g0_input",
    "reverse_direct_edge",
    "split_checker_vertex_id",
    "split_host_element_vertex_id",
]
