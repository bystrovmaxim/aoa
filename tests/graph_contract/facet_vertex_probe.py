# tests/graph_contract/facet_vertex_probe.py
"""
Test-only helpers: collect merged ``FacetVertex`` rows like ``GraphCoordinator.build`` phase 1.

Used by PR3-style tests to feed :mod:`action_machine.graph.graph_builder`
on a coordinator that mirrors :meth:`Core.create_coordinator` registration
order **before** :meth:`GraphCoordinator.build`.
"""

from __future__ import annotations

from action_machine.dependencies.dependency_intent_inspector import DependencyIntentInspector
from action_machine.application import ApplicationContextInspector
from action_machine.intents.domain.entity_intent_inspector import EntityIntentInspector
from action_machine.graph.facet_vertex import FacetVertex
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.intents.aspects.aspect_intent_inspector import AspectIntentInspector
from action_machine.legacy.role_class_inspector import RoleClassInspector
from action_machine.legacy.role_intent_inspector import RoleIntentInspector
from action_machine.legacy.role_mode_intent_inspector import RoleModeIntentInspector
from action_machine.intents.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.intents.compensate.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.intents.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.intents.logging.sensitive_intent_inspector import SensitiveIntentInspector
from action_machine.intents.meta.meta_intent_inspector import MetaIntentInspector
from action_machine.intents.on_error.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.model.base_action import ActionTypedSchemasInspector
from action_machine.resources.connection_intent_inspector import ConnectionIntentInspector


def graph_coordinator_default_inspectors_registered() -> GraphCoordinator:
    """
    Same fluent ``.register(...)`` chain as :meth:`Core.create_coordinator`,
    without calling :meth:`GraphCoordinator.build`.
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
    )


def collect_merged_facet_vertices_unbuilt(coordinator: GraphCoordinator) -> list[FacetVertex]:
    """
    Run phase-1 collection plus ``_materialize_edge_targets`` on an **unbuilt** coordinator.

    Raises:
        RuntimeError: if ``coordinator.build()`` has already completed.
    """
    if coordinator._built:
        msg = "collect_merged_facet_vertices_unbuilt requires a coordinator before build()"
        raise RuntimeError(msg)
    payloads, sources = coordinator._phase1_collect()
    return coordinator._materialize_edge_targets(payloads, sources)
