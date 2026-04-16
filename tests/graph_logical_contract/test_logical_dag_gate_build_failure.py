# tests/graph_logical_contract/test_logical_dag_gate_build_failure.py

"""``GateCoordinator.build`` fails before facet commit when the logical DAG slice cycles."""

from __future__ import annotations

import pytest

from action_machine.graph.logical.logical_graph_builder import LogicalGraphBuilder
from action_machine.graph.logical.model import LogicalEdge, LogicalVertex
from action_machine.model.exceptions import CyclicDependencyError
from action_machine.runtime.machines.core_action_machine import CoreActionMachine


def _v(vid: str) -> LogicalVertex:
    return LogicalVertex(
        id=vid,
        vertex_type="action",
        stereotype="Business Process",
        display_name=vid,
        class_ref=None,
        properties={},
    )


@pytest.mark.graph_coverage
def test_build_raises_cyclic_dependency_when_logical_dag_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cycle_vertices = [_v("a"), _v("b"), _v("c")]
    cycle_edges = [
        LogicalEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    _original_build = LogicalGraphBuilder.__dict__["build"].__func__

    def _patched(
        cls: type[LogicalGraphBuilder],
        *,
        synthetic_g0: object | None = None,
        facet_payloads: object | None = None,
    ) -> tuple[list[LogicalVertex], list[LogicalEdge]]:
        if synthetic_g0 is not None:
            return _original_build(cls, synthetic_g0=synthetic_g0)
        if facet_payloads is not None:
            return cycle_vertices, cycle_edges
        raise AssertionError("LogicalGraphBuilder.build expects one input source")

    monkeypatch.setattr(LogicalGraphBuilder, "build", classmethod(_patched))

    gc = CoreActionMachine.create_coordinator_unbuilt()
    with pytest.raises(CyclicDependencyError, match="cycle"):
        gc.build()
