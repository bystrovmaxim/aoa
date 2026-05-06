# src/action_machine/interchange/vertex_labels.py
"""
Interchange ``node_type`` string constants for facet / graph labeling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

String aliases shared by MCP, viz, and tests; individual graph node classes expose
their own ``NODE_TYPE`` literals.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    graph_model nodes & inspectors ──► these constants ──► HTML / MCP / snapshots

"""

from __future__ import annotations

from typing import Final

# Logical application root interchange ``node_type`` (“Application” row in viz/layout).
APPLICATION_VERTEX_TYPE: Final[str] = "Application"
