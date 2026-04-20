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
"""
