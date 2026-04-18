# src/action_machine/intents/__init__.py
"""
Declarative intent layer for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package defines the intent model used to extend actions with declarative
metadata and behavior contracts. Intents are attached via decorators/markers,
validated by inspectors, and consumed by coordinators at runtime.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Intent definitions are declarative and must not execute business logic.
- Runtime behavior is derived from validated snapshots produced by inspectors.
- Decorators/mixins describe contracts; coordinators orchestrate execution.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action classes/methods
            |
            v
    Decorators + marker intents
            |
            v
    Intent inspectors (validation + snapshot)
            |
            v
    GraphCoordinator facet storage
            |
            v
    Runtime coordinators (auth, logging, plugins, etc.)
            |
            v
    Action execution with consistent policy enforcement

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    An action method is decorated (for example, by plugin/logging decorators),
    inspectors validate intent markers, and runtime coordinators apply policies.

Edge case:
    Invalid intent configuration is rejected during validation, so execution
    fails fast before request handling starts.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Misconfigured intent markers raise validation errors during build/inspection.
- Intent declarations do not replace runtime checks in coordinators.
- This module is documentation-focused and does not expose runtime symbols.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Package-level contract for declarative intent architecture.
CONTRACT: Intents define metadata; inspectors validate; coordinators enforce.
INVARIANTS: Validation precedes runtime usage; snapshots are source of truth.
FLOW: Decorator/marker -> inspector snapshot -> GraphCoordinator -> runtime.
FAILURES: Invalid intent configs fail during inspection, not lazily in runtime.
EXTENSION POINTS: Add new intent modules with marker + inspector + coordinator.
AI-CORE-END
"""
