# src/action_machine/graph/inspectors/__init__.py
"""
Inspector package for ActionMachine graph build pipeline.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package groups concrete ``BaseIntentInspector`` implementations used by
``GateCoordinator`` to materialize facet payloads and snapshots from
decorator-written class metadata.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    decorators write class/method scratch
              │
              ▼
    concrete inspectors scan marker subclasses
              │
              ▼
    inspect(target_cls) -> FacetPayload | None
              │
              ▼
    GateCoordinator.build() validates + commits graph

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Inspectors are stateless class-based components.
- Inspector discovery scope is determined by marker-subclass traversal logic.
- Graph validation/commit orchestration is owned by ``GateCoordinator``, not by this package.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module is an export namespace and does not execute inspection by itself.
- Runtime failures surface from concrete inspector modules or coordinator validation stages.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Namespace for graph intent inspector implementations.
CONTRACT: Organize concrete inspectors consumed by coordinator build process.
INVARIANTS: Inspectors are read-only metadata extractors; coordinator owns transactional build semantics.
FLOW: scratch declarations -> inspector extraction -> payload validation -> graph commit.
FAILURES: Raised in concrete inspectors or coordinator phase checks, not in this namespace file.
EXTENSION POINTS: Add new inspector modules implementing BaseIntentInspector contract.
AI-CORE-END
"""
