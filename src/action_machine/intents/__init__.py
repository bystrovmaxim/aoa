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
    ``NodeGraphCoordinator`` interchange vertices (after ``build()``)
            |
            v
    Runtime coordinators (auth, logging, plugins, etc.)
            |
            v
    Action execution with consistent policy enforcement

"""
