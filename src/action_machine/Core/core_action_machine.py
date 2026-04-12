from __future__ import annotations

from action_machine.aspects.aspect_intent_inspector import AspectIntentInspector
from action_machine.auth.role_class_inspector import RoleClassInspector
from action_machine.auth.role_intent_inspector import RoleIntentInspector
from action_machine.auth.role_mode_intent_inspector import RoleModeIntentInspector
from action_machine.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.compensate.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.core.described_fields_intent import (
    DescribedFieldsIntentInspector,
)
from action_machine.core.meta_intent_inspector import MetaIntentInspector
from action_machine.dependencies.dependency_intent_inspector import (
    DependencyIntentInspector,
)
from action_machine.domain.entity_intent_inspector import EntityIntentInspector
from action_machine.logging.sensitive_intent_inspector import (
    SensitiveIntentInspector,
)
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.on_error.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.plugins.subscription_intent_inspector import (
    SubscriptionIntentInspector,
)
from action_machine.resource_managers.connection_intent_inspector import (
    ConnectionIntentInspector,
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
            .register(AspectIntentInspector)
            .register(CheckerIntentInspector)
            .register(OnErrorIntentInspector)
            .register(CompensateIntentInspector)
            .register(SensitiveIntentInspector)
            .register(SubscriptionIntentInspector)
            .register(EntityIntentInspector)
            .build()
        )
