# tests/graph_contract/facet_vertex_probe.py
"""
Test-only helpers: collect merged ``FacetVertex`` rows like ``GraphCoordinator.build`` phase 1.

Used by PR3-style tests to feed :mod:`graph.graph_builder`
on a coordinator that mirrors :meth:`Core.create_coordinator` registration
order **before** :meth:`GraphCoordinator.build`.

:func:`built_coordinator_with_checker_inspector` adds
:class:`~action_machine.legacy.checker_intent_inspector.CheckerIntentInspector`
before ``build()`` for snapshots that include the ``checker`` facet.
"""

from __future__ import annotations

from action_machine.legacy.checker_intent_inspector import CheckerIntentInspector
from action_machine.legacy.core import Core
from graph.facet_vertex import FacetVertex
from graph.graph_coordinator import GraphCoordinator


def graph_coordinator_default_inspectors_registered() -> GraphCoordinator:
    """
    Same fluent ``.register(...)`` chain as :meth:`Core.create_coordinator`,
    without calling :meth:`GraphCoordinator.build`.
    """
    return Core.register_default_inspectors(GraphCoordinator())


def built_coordinator_with_checker_inspector() -> GraphCoordinator:
    """Production default inspectors plus ``CheckerIntentInspector``, then ``build``.

    Checker facet snapshots are absent from :meth:`~Core.create_coordinator`; bench
    and graph tests that need ``get_snapshot(..., "checker")`` use this helper.
    """
    return Core.register_default_inspectors(GraphCoordinator()).register(
        CheckerIntentInspector,
    ).build()


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
