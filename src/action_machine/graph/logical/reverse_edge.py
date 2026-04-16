# src/action_machine/graph/logical/reverse_edge.py
"""
Build the **reverse** ``LogicalEdge`` for a §5.3 **direct** edge (``graph.md`` v4.1 §11.4).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pure helper used by future ``LogicalGraphBuilder`` and by contract tests so reverse
edge typing stays aligned with ``REVERSE_EDGE_MAP``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only ``category == \"direct\"`` edges with types listed in ``REVERSE_EDGE_MAP`` are reversed.
- Reverse edges use ``category == \"reverse\"``, ``is_dag=False``, and ``stereotype`` from
  ``REVERSE_EDGE_STEREOTYPE`` (spec §5.3 reverse column; not a blind copy of the forward edge).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- ``reverse_direct_edge(BELONGS_TO A→D)`` → ``CONTAINS D→A``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Returns ``None`` when the edge is not a reversible direct edge.
"""

from __future__ import annotations

from typing import Any

from action_machine.graph.logical.constants import REVERSE_EDGE_MAP, REVERSE_EDGE_STEREOTYPE
from action_machine.graph.logical.model import LogicalEdge


def reverse_direct_edge(edge: LogicalEdge) -> LogicalEdge | None:
    """
    Return the paired reverse edge, or ``None`` if ``edge`` is not a direct §5.3 forward edge.
    """
    if edge.category != "direct":
        return None
    reverse_type = REVERSE_EDGE_MAP.get(edge.edge_type)
    if reverse_type is None:
        return None
    rev_st = REVERSE_EDGE_STEREOTYPE.get(edge.edge_type)
    if rev_st is None:
        msg = f"missing REVERSE_EDGE_STEREOTYPE for forward edge type {edge.edge_type!r}"
        raise RuntimeError(msg)
    attrs: dict[str, Any] = dict(edge.attributes) if edge.attributes else {}
    return LogicalEdge(
        source_id=edge.target_id,
        target_id=edge.source_id,
        edge_type=reverse_type,
        stereotype=rev_st,
        category="reverse",
        is_dag=False,
        attributes=attrs,
    )
