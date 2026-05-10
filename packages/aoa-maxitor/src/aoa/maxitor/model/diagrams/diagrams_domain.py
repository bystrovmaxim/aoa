# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/diagrams_domain.py
"""
DiagramsDomain — bounded-context marker for interchange diagram surfaces.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Root bounded context for Maxitor actions and entities tied to the sidebar,
interchange graph, and ERD JSON surfaces (not sample business domains).
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class DiagramsDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Declarative domain for diagram-oriented Maxitor orchestration (G6, ERD, sidebar).
    CONTRACT: ``name`` is ``diagrams``; use with ``@meta(domain=DiagramsDomain)`` / ``@entity(domain=DiagramsDomain)``.
    INVARIANTS: Marker only — no I/O on the class.
    AI-CORE-END
    """

    name = "diagrams"
    description = (
        "Diagrams surface: sidebar menu, interchange graph, ERD rows, and related composition"
    )

