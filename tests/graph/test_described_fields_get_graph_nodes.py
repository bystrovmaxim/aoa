# tests/graph/test_described_fields_get_graph_nodes.py
"""``DescribedFieldsIntentInspector.get_graph_nodes`` for :class:`NodeGraphCoordinator`."""

from __future__ import annotations

from action_machine.common import qualified_dotted_name
from action_machine.graph.node_graph_coordinator import NodeGraphCoordinator
from action_machine.intents.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)

from tests.scenarios.domain_model.ping_action import PingAction


def test_described_fields_get_graph_nodes_emits_sorted_params_and_result_nodes() -> None:
    nodes = DescribedFieldsIntentInspector.get_graph_nodes()
    assert nodes == sorted(nodes, key=lambda n: n.id)
    ids = {n.id for n in nodes}
    assert qualified_dotted_name(PingAction.Params) in ids
    assert qualified_dotted_name(PingAction.Result) in ids
    p = next(n for n in nodes if n.id == qualified_dotted_name(PingAction.Params))
    assert p.node_type == "params_schema"
    assert p.edges == []
    r = next(n for n in nodes if n.id == qualified_dotted_name(PingAction.Result))
    assert r.node_type == "result_schema"
    assert r.edges == []


def test_described_fields_get_graph_nodes_builds_node_graph_coordinator() -> None:
    coord = NodeGraphCoordinator()
    coord.build([DescribedFieldsIntentInspector])
    assert coord.is_built
    g = coord.get_graph()
    assert g.num_nodes() == len(DescribedFieldsIntentInspector.get_graph_nodes())
    assert g.num_edges() == 0
