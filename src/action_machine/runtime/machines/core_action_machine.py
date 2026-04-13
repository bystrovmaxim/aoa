# src/action_machine/runtime/machines/core_action_machine.py
"""
Core coordinator factory for ActionMachine runtime.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module provides a single place to build the default
``GateCoordinator`` instance used by production runtime machines. It registers
the canonical inspector set and returns a built coordinator ready for facet and
graph reads.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Coordinator is always returned in built state.
- Inspector registration order is deterministic and centralized here.
- Default runtime machines rely on this factory for baseline graph contracts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    GateCoordinator()
         |
         v
    register default inspectors (meta/roles/deps/connections/...)
         |
         v
    build graph + facet snapshots
         |
         v
    return built coordinator for runtime machines

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Runtime machine calls ``CoreActionMachine.create_coordinator()`` and gets a
    built coordinator suitable for action execution.

Edge case:
    If custom machine wiring bypasses this factory, caller must ensure
    equivalent inspector registration/build lifecycle.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module defines the default inspector set only.
- Custom coordinator composition belongs to custom machine/bootstrap code.
- Build-time validation failures are surfaced by coordinator/inspectors.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Default coordinator bootstrap factory for runtime entry points.
CONTRACT: create_coordinator() -> built GateCoordinator with canonical inspectors.
INVARIANTS: Deterministic registration order and built return state.
FLOW: construct coordinator -> register inspectors -> build -> hand to runtime.
FAILURES: Inspector/coordinator build errors propagate to caller.
EXTENSION POINTS: Replace with custom bootstrap for alternative inspector sets.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.inspectors.action_typed_schemas_inspector import (
    ActionTypedSchemasInspector,
)
from action_machine.graph.inspectors.aspect_intent_inspector import AspectIntentInspector
from action_machine.graph.inspectors.checker_intent_inspector import CheckerIntentInspector
from action_machine.graph.inspectors.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.graph.inspectors.connection_intent_inspector import (
    ConnectionIntentInspector,
)
from action_machine.graph.inspectors.dependency_intent_inspector import (
    DependencyIntentInspector,
)
from action_machine.graph.inspectors.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.graph.inspectors.entity_intent_inspector import EntityIntentInspector
from action_machine.graph.inspectors.meta_intent_inspector import MetaIntentInspector
from action_machine.graph.inspectors.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.graph.inspectors.role_class_inspector import RoleClassInspector
from action_machine.graph.inspectors.role_intent_inspector import RoleIntentInspector
from action_machine.graph.inspectors.role_mode_intent_inspector import RoleModeIntentInspector
from action_machine.graph.inspectors.sensitive_intent_inspector import (
    SensitiveIntentInspector,
)
from action_machine.graph.inspectors.subscription_intent_inspector import (
    SubscriptionIntentInspector,
)


class CoreActionMachine:
    """Core factory for creating a fully built coordinator."""

    @staticmethod
    def create_coordinator() -> GateCoordinator:
        """
        Create coordinator, register all default inspectors and build the graph.

        Returns:
            Built ``GateCoordinator`` instance ready for snapshot reads.
        """
        return (
            GateCoordinator()
            .register(MetaIntentInspector)
            .register(RoleIntentInspector)
            .register(RoleModeIntentInspector)
            .register(RoleClassInspector)
            .register(DependencyIntentInspector)
            .register(ConnectionIntentInspector)
            .register(DescribedFieldsIntentInspector)
            .register(ActionTypedSchemasInspector)
            .register(AspectIntentInspector)
            .register(CheckerIntentInspector)
            .register(OnErrorIntentInspector)
            .register(CompensateIntentInspector)
            .register(SensitiveIntentInspector)
            .register(SubscriptionIntentInspector)
            .register(EntityIntentInspector)
            .build()
        )
