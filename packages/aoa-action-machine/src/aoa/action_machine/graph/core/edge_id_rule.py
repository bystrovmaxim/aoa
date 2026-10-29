# packages/aoa-action-machine/src/aoa/action_machine/graph/core/edge_id_rule.py
"""
EdgeIdRule — what an edge type adds to, or puts in place of, the default edge id.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An exported edge is named ``<source_id>|<type>|<target_id>`` by default. A type whose
edges can repeat between the same two nodes declares an :class:`EdgeIdRule` on its edge
class: a **member** property that names the edge in place of its target, or a **suffix**
property appended to the id. The id itself is computed by
:func:`aoa.action_machine.graph.edge_identity.edge_id`, which re-exports this module.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    edge class (EDGE_TYPE, ID_RULE: EdgeIdRule)  ──►  edge_identity.EDGE_ID_RULES  ──►  edge_id(row)

This module imports nothing from the graph, so edge classes can import it while
``edge_identity`` imports those classes.
"""

from __future__ import annotations

from dataclasses import dataclass

EDGE_SEPARATOR: str = "|"


@dataclass(frozen=True)
class EdgeIdRule:
    """
    AI-CORE-BEGIN
    ROLE: Declares how one edge type's id differs from the default ``<source_id>|<type>|<target_id>``.
    CONTRACT: ``member`` names the property that stands in place of the target; ``suffix`` names the property appended after it.
    INVARIANTS: At most one of the two is set; both empty means the default rule.
    FAILURES: ``ValueError`` when both are set.
    AI-CORE-END
    """

    member: str | None = None
    suffix: str | None = None

    def __post_init__(self) -> None:
        """Refuse a rule that sets both a member and a suffix."""
        if self.member is not None and self.suffix is not None:
            raise ValueError(f"EdgeIdRule sets both member {self.member!r} and suffix {self.suffix!r}; set at most one.")
