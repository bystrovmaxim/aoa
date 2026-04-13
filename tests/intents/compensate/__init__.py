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

test_compensate_intent_validators.py
    Compensator intent validators and typed snapshots.

tests/scenarios/intents_with_runtime/test_compensate_graph.py
    GateCoordinator graph: compensator nodes, has_compensator / requires_context edges;
    traversal via get_nodes_for_class / graph primitives.

test_saga_rollback.py
    Core rollback: SagaFrame stack unwinding in ActionProductMachine._rollback_saga():
    call order and data (params, state_before, state_after, error).

test_saga_errors.py
    Silent compensator errors: failure does not stop rollback; all compensators run;
    @on_error receives the original aspect error.

test_saga_events.py
    Typed plugin events: SagaRollbackStartedEvent, SagaRollbackCompletedEvent,
    BeforeCompensateAspectEvent, AfterCompensateAspectEvent, CompensateFailedEvent.

test_saga_rollup.py
    rollup=True: compensators are not invoked; Saga events are not emitted.

test_saga_order.py
    Error handling order: compensation runs before @on_error.

tests/scenarios/intents_with_runtime/test_saga_nested.py
    Nested box.run() calls: per-level stack isolation and interaction with try/except
    in aspects.

test_saga_integration.py
    End-to-end scenarios: multiple aspects + compensators + @on_error, compensator
    with @context_requires.
"""
