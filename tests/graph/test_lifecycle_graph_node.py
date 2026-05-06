# tests/graph/test_lifecycle_graph_node.py
"""Lifecycle graph node edge emission."""

from __future__ import annotations

import pytest

from action_machine.domain.exceptions import LifecycleGraphError
from action_machine.domain.lifecycle import Lifecycle
from action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from action_machine.graph_model.nodes.state_graph_node import StateGraphNode


class _Host:
    pass


class _Lifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("recorded", "Recorded").to("settled").initial()
        .state("settled", "Settled").final()
    )


def test_lifecycle_graph_node_edges_include_initial_state_attachment() -> None:
    node = LifeCycleGraphNode(_Host, "status", _Lifecycle)

    edges = node.get_all_edges()

    contains = [edge for edge in edges if edge.edge_name == "lifecycle_contains_state"]
    transitions = [edge for edge in edges if edge.edge_name == "lifecycle_transition"]

    assert {edge.properties["state_key"] for edge in contains} == {"recorded", "settled"}
    assert any(edge.target_node_id.endswith(":recorded") for edge in contains)
    assert [(edge.properties["from_state"], edge.properties["to_state"]) for edge in transitions] == [
        ("recorded", "settled"),
    ]


def test_state_graph_node_rejects_lifecycle_without_template() -> None:
    class _NoTemplateLifecycle(Lifecycle):
        pass

    with pytest.raises(LifecycleGraphError):
        StateGraphNode(_NoTemplateLifecycle, "recorded", "host:status")
