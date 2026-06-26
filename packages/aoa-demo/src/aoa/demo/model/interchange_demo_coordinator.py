# packages/aoa-demo/src/aoa/demo/model/interchange_demo_coordinator.py
"""
Interchange coordinator for HTML demos — one graph build for all visualizers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ERD graph JSON (diagram serializers in :mod:`aoa.maxitor.model.diagrams.actions.list_entities_action`)
and the interchange graph visualizer via diagrams interchange graph helpers both consume a built
:class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`. This module is the single
construction path for demos so both exports see identical topology after sample registration.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Call :func:`import_sample_registration_modules` then
:func:`build_registered_interchange_coordinator`. Production coordinator is attempted first;
:class:`~aoa.action_machine.graph.core.debug_node_graph_coordinator.DebugNodeGraphCoordinator` is used when sample
graphs violate DAG rules (cycles).

When tests are run with ``pytest`` in the same interpreter, the built coordinator and sample imports
are cached process-wide so repeated ASGI lifespans and coordinator probes reuse one graph build.
"""

from __future__ import annotations

import importlib
import sys

from aoa.action_machine.graph.core.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.node_graph_coordinator_factory import (
    GRAPH_JSON_SCHEMA,
    all_axis_graph_node_inspectors,
    create_node_graph_coordinator,
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
    """Import same modules as ``aoa.demo.model.build`` for registration side effects."""
    if _pytest_demo_cache_enabled() and _demo_pytest_cache.modules_done:
        return
    from aoa.demo.model.build import _MODULES  # pylint: disable=import-outside-toplevel

    for name in _MODULES:
        importlib.import_module(name)
    if _pytest_demo_cache_enabled():
        _demo_pytest_cache.modules_done = True


def build_registered_interchange_coordinator() -> NodeGraphCoordinator:
    """
    Build interchange graph after intents are registered.

    AI-CORE-BEGIN
    CONTRACT: Mirrors production :func:`aoa.action_machine.graph.node_graph_coordinator_factory.create_node_graph_coordinator` when DAG-valid; falls back to
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
