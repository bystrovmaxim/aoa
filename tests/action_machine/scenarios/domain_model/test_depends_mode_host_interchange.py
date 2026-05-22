# tests/action_machine/scenarios/domain_model/test_depends_mode_host_interchange.py
"""Runtime wiring checks for ``DependsModeHostAction`` (graph layer must not import ``runtime``)."""

from __future__ import annotations

from aoa.action_machine.graph.edges.depends_graph_edge import DependsGraphEdge
from aoa.action_machine.intents.depends import UseCase
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

from .depends_mode_host_action import DependsModeHostAction
from .ping_action import PingAction
from .services import PaymentServiceResource

PING_CLS = PingAction
PAYMENT_CLS = PaymentServiceResource


def test_resource_depend_edge_wire_json_omits_mode_key() -> None:
    """PR-5: canonical check — resource ``@depends`` must not emit ``mode`` in wire JSON."""
    machine = ActionProductMachine()
    host_id = machine.get_action_node_by_id(DependsModeHostAction).node_id
    edges = DependsGraphEdge.get_dependency_edges(DependsModeHostAction)
    payment_edge = next(e for e in edges if e.target_node_id.rsplit(".", 1)[-1] == "PaymentServiceResource")
    result = payment_edge.to_dict(source_id=host_id)
    assert "mode" not in result["properties"]


def test_resolved_dependency_infos_round_trips_mode_from_wired_edges() -> None:
    machine = ActionProductMachine()
    node = machine.get_action_node_by_id(DependsModeHostAction)
    infos = node.resolved_dependency_infos()
    modes_by_cls = {info.cls: info.mode for info in infos}
    assert modes_by_cls[PING_CLS] == UseCase.include
    assert modes_by_cls[PAYMENT_CLS] is None
