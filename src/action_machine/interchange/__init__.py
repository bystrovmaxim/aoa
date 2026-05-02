# src/action_machine/interchange/__init__.py
"""
Interchange — shared ``node_type`` string aliases for facet graphs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Keeps interchange vertex literals in a shallow package so MCP, viz, and tests
can share strings without importing the full :mod:`graph` coordinator surface.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors emit ``node_type`` strings
              │
              ▼
              vertex_labels (shared aliases)

"""
