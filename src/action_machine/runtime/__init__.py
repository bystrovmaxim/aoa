# src/action_machine/runtime/__init__.py
"""
Runtime package public entry points.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exposes runtime machine APIs, binding helpers, and execution
components used to run ActionMachine actions in production.

Canonical coordinator assembly lives in ``Core``: it creates a
``GraphCoordinator``, registers default inspectors, and builds the graph/facets.
Production machines consume a built coordinator as a fail-fast contract.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``ActionProductMachine`` reads pipeline metadata from coordinator snapshots only.
- ``Core`` is exported lazily through ``__getattr__``.
- Public runtime interfaces remain stable while internal composition can evolve.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Runtime package import
           |
           +--> lightweight modules (navigation, components)
           |
           +--> lazy Core access via __getattr__ (Core lives in ``action_machine.legacy.core``)
                         |
                         v
                create/build GraphCoordinator
                         |
                         v
                runtime machine execution pipeline

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Runtime consumers import and use machine classes while coordinator assembly
    is provided by ``Core`` when needed.

Edge case:
    Lazy export avoids graph-stack imports during early module initialization,
    preventing circular/lifecycle issues around model bootstrap.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Accessing unknown attributes through package ``__getattr__`` raises ``AttributeError``.
- This module does not implement runtime execution logic directly.
- Coordinator validity/build errors are surfaced by machine/factory modules.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Runtime package-level API and lazy export gateway.
CONTRACT: Expose Core lazily; preserve runtime import safety.
INVARIANTS: Snapshot-driven runtime semantics and fail-fast coordinator build.
FLOW: package import -> lazy core access -> coordinator build -> machine run.
FAILURES: Unknown attribute access errors and downstream coordinator/runtime errors.
EXTENSION POINTS: Add exports without breaking lazy-import safety guarantees.
AI-CORE-END
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.legacy.core import Core

__all__ = ["Core"]


def __getattr__(name: str) -> object:
    if name == "Core":
        from action_machine.legacy.core import Core  # pylint: disable=import-outside-toplevel

        return Core
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
