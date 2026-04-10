from __future__ import annotations

from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector
from action_machine.auth.role_gate_host_inspector import RoleGateHostInspector
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.core.described_fields_gate_host import (
    DescribedFieldsGateHostInspector,
)
from action_machine.core.meta_gate_host_inspector import MetaGateHostInspector
from action_machine.dependencies.dependency_gate_host_inspector import (
    DependencyGateHostInspector,
)
from action_machine.domain.entity_gate_host_inspector import EntityGateHostInspector
from action_machine.logging.sensitive_gate_host_inspector import (
    SensitiveGateHostInspector,
)
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.on_error.on_error_gate_host_inspector import OnErrorGateHostInspector
from action_machine.plugins.subscription_gate_host_inspector import (
    SubscriptionGateHostInspector,
)
from action_machine.resource_managers.connection_gate_host_inspector import (
    ConnectionGateHostInspector,
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
            .register(MetaGateHostInspector)
            .register(RoleGateHostInspector)
            .register(DependencyGateHostInspector)
            .register(ConnectionGateHostInspector)
            .register(DescribedFieldsGateHostInspector)
            .register(AspectGateHostInspector)
            .register(CheckerGateHostInspector)
            .register(OnErrorGateHostInspector)
            .register(CompensateGateHostInspector)
            .register(SensitiveGateHostInspector)
            .register(SubscriptionGateHostInspector)
            .register(EntityGateHostInspector)
            .build()
        )

