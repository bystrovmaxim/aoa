# src/action_machine/legacy/binding/__init__.py
"""
Runtime binding helpers for action generic contracts.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package groups helpers that resolve and validate runtime bindings for
``BaseAction[P, R]`` generics. It supports extraction of declared result type
and consistency checks for values produced by summary/on_error handlers.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class BaseAction[P, R]
               |
               v
    Binding helpers resolve declared generic types
               |
               v
    Runtime validates produced result instance type
               |
               v
    Adapter/caller receives contract-safe result value

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Runtime resolves ``R`` for an action and confirms summary output is an
    instance of that result type.

Edge case:
    If runtime receives a result with mismatched type, binding validation
    raises a typed contract exception.
"""
