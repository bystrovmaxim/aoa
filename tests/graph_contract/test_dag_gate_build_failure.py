# tests/graph_contract/test_dag_gate_build_failure.py

"""``GraphCoordinator.build`` fails before facet commit when the interchange DAG slice cycles."""

from __future__ import annotations

import pytest

import action_machine.graph.graph_coordinator as gate_coordinator_mod
from action_machine.graph.model import GraphEdge, GraphVertex
from action_machine.model.exceptions import CyclicDependencyError

from .facet_payload_probe import graph_coordinator_default_inspectors_registered


def _v(vid: str) -> GraphVertex:
    return GraphVertex(
        id=vid,
        node_type="action",
        stereotype="Business Process",
        label=vid,
        class_ref=None,
        properties={},
    )


@pytest.mark.graph_coverage
def test_build_raises_cyclic_dependency_when_dag_slice_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cycle_vertices = [_v("a"), _v("b"), _v("c")]
    cycle_edges = [
        GraphEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    def _patched(
        _payloads: object,
    ) -> tuple[list[GraphVertex], list[GraphEdge]]:
        return cycle_vertices, cycle_edges

    monkeypatch.setattr(
        gate_coordinator_mod,
        "build_interchange_from_facet_payloads",
        _patched,
    )

    gc = graph_coordinator_default_inspectors_registered()
    with pytest.raises(CyclicDependencyError, match="cycle"):
        gc.build()
