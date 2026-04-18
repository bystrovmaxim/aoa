# src/action_machine/runtime/machines/core.py
"""
Core coordinator factory for ActionMachine runtime.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module provides a single place to build the default
``GraphCoordinator`` instance used by production runtime machines. It registers
the canonical inspector set and returns a built coordinator ready for facet and
graph reads.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Coordinator is always returned in built state from :meth:`Core.create_coordinator`.
- Inspector registration order is deterministic and centralized here.
- Default runtime machines rely on this factory for baseline graph contracts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    GraphCoordinator()
         |
         v
    fluent .register(...) for each default inspector
         |
         v
    build interchange graph + facet snapshots
         |
         v
    return built coordinator for runtime machines

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Runtime machine calls ``Core.create_coordinator()`` and gets a
    built coordinator suitable for action execution.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module defines the default inspector set only.
- Custom coordinator composition belongs to custom machine/bootstrap code.
- Build-time validation failures are surfaced by coordinator/inspectors.
- ``EntityIntentInspector`` is registered here; interchange graph includes
  ``entity:<name>`` vertices from facet payloads (see ``maxitor.samples.store.entities`` in the sample bundle).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Default coordinator bootstrap factory for runtime entry points.
CONTRACT: create_coordinator() -> built GraphCoordinator with canonical inspectors.
INVARIANTS: Deterministic registration order and built return state.
FLOW: construct coordinator -> register inspectors -> build -> hand to runtime.
FAILURES: Inspector/coordinator build errors propagate to caller.
EXTENSION POINTS: Replace with custom bootstrap for alternative inspector sets.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.dependencies.dependency_intent_inspector import (
    DependencyIntentInspector,
)
from action_machine.domain.application_context_inspector import (
    ApplicationContextInspector,
)
from action_machine.domain.entity_intent_inspector import EntityIntentInspector
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.intents.aspects.aspect_intent_inspector import AspectIntentInspector
from action_machine.intents.auth.role_class_inspector import RoleClassInspector
from action_machine.intents.auth.role_intent_inspector import RoleIntentInspector
from action_machine.intents.auth.role_mode_intent_inspector import RoleModeIntentInspector
from action_machine.intents.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.intents.compensate.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.intents.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.intents.logging.sensitive_intent_inspector import (
    SensitiveIntentInspector,
)
from action_machine.intents.meta.meta_intent_inspector import MetaIntentInspector
from action_machine.intents.on_error.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.model.base_action import ActionTypedSchemasInspector
from action_machine.resources.connection_intent_inspector import (
    ConnectionIntentInspector,
)


class Core:
    """Core factory for creating a fully built coordinator."""

    @staticmethod
    def create_coordinator() -> GraphCoordinator:
        """
        Create a ``GraphCoordinator``, register all default inspectors, and build.

        Returns:
            Built ``GraphCoordinator`` instance ready for snapshot reads.
        """
        return (
            GraphCoordinator()
            .register(ApplicationContextInspector)
            .register(MetaIntentInspector)
            .register(RoleClassInspector)
            .register(RoleIntentInspector)
            .register(RoleModeIntentInspector)
            .register(DependencyIntentInspector)
            .register(ConnectionIntentInspector)
            .register(DescribedFieldsIntentInspector)
            .register(ActionTypedSchemasInspector)
            .register(AspectIntentInspector)
            .register(CheckerIntentInspector)
            .register(OnErrorIntentInspector)
            .register(CompensateIntentInspector)
            .register(SensitiveIntentInspector)
            .register(EntityIntentInspector)
            .build()
        )
