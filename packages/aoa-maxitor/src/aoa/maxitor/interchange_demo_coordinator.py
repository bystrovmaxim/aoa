# packages/aoa-maxitor/src/aoa/maxitor/interchange_demo_coordinator.py
"""
Interchange coordinator for Maxitor HTML demos — one graph build for all visualizers.

Same behaviour as ``aoa.examples.model.interchange_demo_coordinator`` but keeps the sample
module list here so ``aoa-maxitor`` does not depend on the ``aoa-examples`` distribution.
Importing those modules still requires ``aoa.examples.*`` on ``PYTHONPATH`` (install
``aoa-examples`` or use the meta ``aoa-run`` workspace).

Keep :data:`SAMPLE_MODEL_REGISTRATION_MODULE_NAMES` in sync with ``_MODULES`` in
``aoa.examples.model.build``.
"""

from __future__ import annotations

import importlib
import sys
from typing import Final

from aoa.action_machine.graph_model.node_graph_coordinator_factory import (
    GRAPH_JSON_SCHEMA,
    all_axis_graph_node_inspectors,
    create_node_graph_coordinator,
)
from aoa.graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.graph.exceptions import InvalidGraphError
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator

SAMPLE_MODEL_REGISTRATION_MODULE_NAMES: Final[tuple[str, ...]] = (
    "aoa.examples.model.roles",
    # billing: full contour, matching store depth
    "aoa.examples.model.billing.domain",
    "aoa.examples.model.billing.entities",
    "aoa.examples.model.billing.dependencies",
    "aoa.examples.model.billing.resources",
    "aoa.examples.model.billing.plugins",
    "aoa.examples.model.billing.actions",
    # messaging
    "aoa.examples.model.messaging.domain",
    "aoa.examples.model.messaging.entities",
    "aoa.examples.model.messaging.dependencies",
    "aoa.examples.model.messaging",
    "aoa.examples.model.messaging.resources",
    "aoa.examples.model.messaging.plugins",
    "aoa.examples.model.messaging.actions",
    # catalog
    "aoa.examples.model.catalog.domain",
    "aoa.examples.model.catalog.entities",
    "aoa.examples.model.catalog.dependencies",
    "aoa.examples.model.catalog.resources",
    "aoa.examples.model.catalog.plugins",
    # synthetic domains for heterogeneous ERD / graph cardinality demos
    "aoa.examples.model.identity.domain",
    "aoa.examples.model.identity.entities",
    "aoa.examples.model.inventory.domain",
    "aoa.examples.model.inventory.entities",
    "aoa.examples.model.analytics.domain",
    "aoa.examples.model.analytics.entities",
    # ERD topology echoes: clinical intake/dispatch mesh + QA portfolio mesh
    "aoa.examples.model.clinical_supply.domain",
    "aoa.examples.model.clinical_supply.entities",
    "aoa.examples.model.assurance_portfolio.domain",
    "aoa.examples.model.assurance_portfolio.entities",
    # store (depends on billing/messaging services)
    "aoa.examples.model.store.marketplace_operations_domain",
    "aoa.examples.model.store.store_domain",
    "aoa.examples.model.store.dependencies",
    "aoa.examples.model.store.entities",
    "aoa.examples.model.store.resources",
    "aoa.examples.model.store.plugins",
    "aoa.examples.model.catalog.actions",
    "aoa.examples.model.store.actions",
    # entity wire projection demo (PR-5)
    "aoa.examples.model.entity_projection_demo.domain",
    "aoa.examples.model.entity_projection_demo.entities",
    "aoa.examples.model.entity_projection_demo.actions",
    # support: @depends on BaseAction in the same domain and in store
    "aoa.examples.model.support.support_domain",
    "aoa.examples.model.support.entities",
    "aoa.examples.model.support.actions",
    # operational slices mirroring heavyweight use-case cardinality (diagram harnesses)
    "aoa.examples.model.catalog_custody.catalog_custody_domain",
    "aoa.examples.model.catalog_custody.entities",
    "aoa.examples.model.catalog_custody.actions",
    "aoa.examples.model.settlement_desks.settlement_desks_domain",
    "aoa.examples.model.settlement_desks.entities",
    "aoa.examples.model.settlement_desks.actions",
    "aoa.examples.model.telemetry_pipeline.telemetry_pipeline_domain",
    "aoa.examples.model.telemetry_pipeline.entities",
    "aoa.examples.model.telemetry_pipeline.actions",
    "aoa.examples.model.logistics_mesh.logistics_mesh_domain",
    "aoa.examples.model.logistics_mesh.entities",
    "aoa.examples.model.logistics_mesh.actions",
)


class _PytestDemoBuildCache:
    """Mutable process-local cache (avoids ``global`` in module-level helpers)."""

    __slots__ = ("coordinator", "modules_done", "pytest_active")

    def __init__(self) -> None:
        self.pytest_active: bool | None = None
        self.modules_done: bool = False
        self.coordinator: NodeGraphCoordinator | None = None


_demo_pytest_cache = _PytestDemoBuildCache()


def _pytest_demo_cache_enabled() -> bool:
    """Reuse one coordinator across pytest (same process) — graph build + sample imports are costly."""
    if _demo_pytest_cache.pytest_active is None:
        _demo_pytest_cache.pytest_active = "pytest" in sys.modules
    return _demo_pytest_cache.pytest_active


def import_sample_registration_modules() -> None:
    """Import sample model packages for registration side effects."""
    if _pytest_demo_cache_enabled() and _demo_pytest_cache.modules_done:
        return
    for name in SAMPLE_MODEL_REGISTRATION_MODULE_NAMES:
        importlib.import_module(name)
    if _pytest_demo_cache_enabled():
        _demo_pytest_cache.modules_done = True


def build_registered_interchange_coordinator() -> NodeGraphCoordinator:
    """
    Build interchange graph after intents are registered.

    AI-CORE-BEGIN
    CONTRACT: Mirrors production :func:`aoa.action_machine.graph_model.node_graph_coordinator_factory.create_node_graph_coordinator` when DAG-valid; falls back to
        ``DebugNodeGraphCoordinator`` plus ``build(all_axis_graph_node_inspectors())`` otherwise.
    INVARIANTS: Caller must register samples via :func:`import_sample_registration_modules` first.
    AI-CORE-END
    """
    if _pytest_demo_cache_enabled() and _demo_pytest_cache.coordinator is not None:
        return _demo_pytest_cache.coordinator
    import_sample_registration_modules()
    try:
        coord = create_node_graph_coordinator()
    except InvalidGraphError:
        coord = DebugNodeGraphCoordinator()
        coord.build(all_axis_graph_node_inspectors(), export_json_schema=GRAPH_JSON_SCHEMA)
    if _pytest_demo_cache_enabled():
        _demo_pytest_cache.coordinator = coord
    return coord
