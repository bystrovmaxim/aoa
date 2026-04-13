# src/action_machine/runtime/machines/core_action_machine.py
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
