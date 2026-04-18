# tests/graph_contract/facet_payload_probe.py
"""
Test-only helpers: collect merged ``FacetPayload`` rows like ``GateCoordinator.build`` phase 1.

Used by PR3-style tests to feed :mod:`action_machine.graph.graph_builder`
on a coordinator that mirrors :meth:`CoreActionMachine.create_coordinator` registration
order **before** :meth:`GateCoordinator.build`.
"""

from __future__ import annotations

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.model.base_action import ActionTypedSchemasInspector
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
from action_machine.graph.payload import FacetPayload


def gate_coordinator_default_inspectors_registered() -> GateCoordinator:
    """
    Same fluent ``.register(...)`` chain as :meth:`CoreActionMachine.create_coordinator`,
    without calling :meth:`GateCoordinator.build`.
    """
    return (
        GateCoordinator()
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
    )


def collect_merged_facet_payloads_unbuilt(coordinator: GateCoordinator) -> list[FacetPayload]:
    """
    Run phase-1 collection plus ``_materialize_edge_targets`` on an **unbuilt** coordinator.

    Raises:
        RuntimeError: if ``coordinator.build()`` has already completed.
    """
    if coordinator._built:
        msg = "collect_merged_facet_payloads_unbuilt requires a coordinator before build()"
        raise RuntimeError(msg)
    payloads, sources = coordinator._phase1_collect()
    return coordinator._materialize_edge_targets(payloads, sources)
