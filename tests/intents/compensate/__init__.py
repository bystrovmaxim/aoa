# tests/intents/compensate/__init__.py
"""
Tests for the ActionMachine compensation (Saga) mechanism.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Tests the Saga-style compensation pattern in ActionMachine, organized by concern:

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

test_compensate_decorator.py
    @compensate validation at class definition (import time): arguments, types, name
    suffix, signature.

tests/scenarios/intents_with_runtime/test_compensate_graph.py
    GraphCoordinator graph: compensator nodes, has_compensator / requires_context edges;
    traversal via get_nodes_for_class / graph primitives.

test_saga_rollback.py
    Compensator return value is ignored during saga unwind.
"""
