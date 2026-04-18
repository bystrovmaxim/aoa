# src/action_machine/runtime/machines/__init__.py
"""
Runtime machine package public API.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exposes production machine entry points for ActionMachine runtime:
async/sync executors and ``CoreActionMachine`` coordinator-aware factory.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Runtime machine APIs execute action pipeline contracts from coordinator snapshots.
- Sync and async machine variants preserve shared validation/orchestration semantics.
- ``CoreActionMachine`` remains the integration entry for coordinator-driven wiring.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    GraphCoordinator (built graph + facets)
               |
               v
    CoreActionMachine factory / wiring
               |
        +------+------+
        |             |
        v             v
    Async machine   Sync machine
        |             |
        +------+------+
               |
               v
    Action execution with runtime components and typed result

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    App creates coordinator graph, builds machine instance from this package,
    and executes actions through a stable runtime pipeline.

Edge case:
    Runtime contract violations (roles, connections, result type) are surfaced
    by machine execution path using typed framework exceptions.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module is an export surface and does not implement machine internals.
- Concrete behavior depends on selected machine class and injected components.
- Snapshot/build lifecycle must complete before machine execution.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public gateway for runtime machine implementations.
CONTRACT: Expose core async/sync machine entry points with shared semantics.
INVARIANTS: Execution contracts derive from GraphCoordinator snapshots.
FLOW: coordinator build -> machine creation -> action run -> typed outputs/events.
FAILURES: Runtime contract breaches propagate as typed framework errors.
EXTENSION POINTS: Swap machine/component implementations behind same API surface.
AI-CORE-END
"""
