# tests/graph_contract/facet_vertex_probe.py
"""
Test-only helpers: collect merged ``FacetVertex`` rows like ``GraphCoordinator.build`` phase 1.

Used by PR3-style tests to feed :mod:`graph.graph_builder`
on a coordinator that mirrors :meth:`Core.create_coordinator` registration
order **before** :meth:`GraphCoordinator.build`. Checker facets for tests live in
:class:`Core`'s separate :meth:`~Core.create_coordinator_with_checker_inspector`.
"""

from __future__ import annotations

from action_machine.legacy.core import Core
from graph.facet_vertex import FacetVertex
from graph.graph_coordinator import GraphCoordinator


def graph_coordinator_default_inspectors_registered() -> GraphCoordinator:
    """
    Same fluent ``.register(...)`` chain as :meth:`Core.create_coordinator`,
    without calling :meth:`GraphCoordinator.build`.
    """
    return Core.register_default_inspectors(GraphCoordinator())


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
