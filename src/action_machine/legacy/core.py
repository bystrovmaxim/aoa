# src/action_machine/legacy/core.py
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

"""

from __future__ import annotations

from action_machine.legacy.application_context_inspector import ApplicationContextInspector
from action_machine.legacy.aspect_intent_inspector import AspectIntentInspector
from action_machine.legacy.checker_intent_inspector import CheckerIntentInspector
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.legacy.connection_intent_inspector import (
    ConnectionIntentInspector,
)
from action_machine.legacy.dependency_intent_inspector import (
    DependencyIntentInspector,
)
from action_machine.legacy.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.legacy.entity_intent_inspector import EntityIntentInspector
from action_machine.legacy.meta_intent_inspector import MetaIntentInspector
from action_machine.legacy.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.legacy.role_class_inspector import RoleClassInspector
from action_machine.legacy.role_intent_inspector import RoleIntentInspector
from action_machine.legacy.role_mode_intent_inspector import RoleModeIntentInspector
from action_machine.legacy.sensitive_intent_inspector import (
    SensitiveIntentInspector,
)
from action_machine.model.base_action import ActionTypedSchemasInspector
from graph.graph_coordinator import GraphCoordinator


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
