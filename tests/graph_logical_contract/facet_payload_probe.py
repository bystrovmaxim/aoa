# tests/graph_logical_contract/facet_payload_probe.py
"""
Test-only helpers: collect merged ``FacetPayload`` rows like ``GateCoordinator.build`` phase 1.

Used by PR3-style tests to feed :class:`~action_machine.graph.logical.LogicalGraphBuilder`
without changing ``GateCoordinator`` public behaviour beyond ``create_coordinator_unbuilt``.
"""

from __future__ import annotations

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.payload import FacetPayload


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
