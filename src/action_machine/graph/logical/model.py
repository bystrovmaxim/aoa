# src/action_machine/graph/logical/model.py
"""
Frozen datatypes for the **logical coordinator graph** (spec graph.md §10, subset for G0).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide transport types for logical vertices and edges so golden tests and future
``LogicalGraphBuilder`` share one canonical shape independent of ``rustworkx``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    JSON / facet bundle  →  builder  →  tuple[list[LogicalVertex], list[LogicalEdge]]
                                    →  canonical dicts  →  golden compare

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Instances are immutable (``frozen=True``).
- ``id`` values are stable qualified names or composite ids from the specification.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- ``LogicalVertex(id="pkg.actions.Foo", vertex_type="action", stereotype="...", ...)``
- ``LogicalEdge(..., edge_type="BELONGS_TO", stereotype="...", category="direct", ...)``

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation here; callers (builder, tests) enforce referential integrity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogicalVertex:
    """One logical graph vertex."""

    id: str
    vertex_type: str
    stereotype: str
    display_name: str
    class_ref: type | None
    properties: dict[str, Any]


@dataclass(frozen=True)
class LogicalEdge:
    """One directed logical graph edge."""

    source_id: str
    target_id: str
    edge_type: str
    stereotype: str
    category: str
    is_dag: bool
    attributes: dict[str, Any]
