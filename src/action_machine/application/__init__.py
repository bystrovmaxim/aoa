# src/action_machine/application/__init__.py
"""
Application — logical root facet and ``BaseDomain`` → ``Application`` graph wiring.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exposes the marker :class:`ApplicationContext` and
:class:`ApplicationContextInspector`, which register the coordinator ``Application``
vertex and ``belongs_to`` edges from materialized ``BaseDomain`` types.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ApplicationContext  (marker)
           ^
           |  ``belongs_to`` (informational)
    BaseDomain subclasses  →  ApplicationContextInspector  →  FacetVertex rows

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``ApplicationContext`` carries no runtime state; it names one logical graph anchor.
- The inspector targets ``BaseDomain`` and merges the shared Application node across domains.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from action_machine.application import ApplicationContext
    from action_machine.legacy.core import Core

    Core.create_coordinator()  # registers ApplicationContextInspector

Edge case: abstract ``BaseDomain`` is skipped; concrete leaf domains with valid ``name`` / ``description`` emit facets.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Domain rows without full metadata are skipped by :meth:`ApplicationContextInspector.inspect`.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Package for Application facet marker and BaseDomain→Application inspector.
CONTRACT: Export ApplicationContext and ApplicationContextInspector for coordinator registration.
INVARIANTS: Marker is graph identity only; inspector inherits BaseIntentInspector behavior.
FLOW: import -> Core or test probe -> register on GraphCoordinator -> build graph.
EXTENSION POINTS: Additional application-scoped facets can live alongside these modules.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from .application_context import ApplicationContext
from .application_context_inspector import ApplicationContextInspector

__all__ = [
    "ApplicationContext",
    "ApplicationContextInspector",
]
