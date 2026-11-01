# tests/graph/test_lifecycle_graph_node.py
"""Lifecycle graph node edge emission and state-row content."""

from __future__ import annotations

import jsonschema
import pytest
from pydantic import ConfigDict, Field
from pydantic_core import PydanticSerializationError

from aoa.action_machine.domain import BaseStateEntity
from aoa.action_machine.domain.exceptions import LifecycleGraphError
from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.lifecycle_graph_node import LifeCycleGraphNode
from aoa.action_machine.graph.nodes.state_graph_node import StateGraphNode


class _Host:
    pass


class _SampleStateEntity(BaseStateEntity):
    """Status used by the state-row tests."""

    sort_order: int = Field(default=0, description="Presentation order")
    secret: str = Field(default="hidden", description="Internal", exclude=True)


class _Lifecycle(Lifecycle):
    """The chain the state-row tests read."""

    RECORDED = _SampleStateEntity(code="recorded", display_name="Recorded", sort_order=1)
    SETTLED = _SampleStateEntity(code="settled", display_name="Settled", sort_order=2)

    _template = (
        Lifecycle()
        .state(RECORDED).to(SETTLED).initial()
        .state(SETTLED).final()
    )


def _state_rows() -> list[dict[str, object]]:
    node = LifeCycleGraphNode(_Host, "status", _Lifecycle)
    return [state.to_dict() for state in node.states]


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


def test_state_row_keeps_the_template_id_and_kind() -> None:
    node = LifeCycleGraphNode(_Host, "status", _Lifecycle)
    expected = {"recorded": "StateInitial", "settled": "StateFinal"}

    for state in node.states:
        row = state.to_dict()
        assert row["id"] == f"{node.node_id}:{state.node_obj.state_key}"
        assert row["type"] == expected[state.node_obj.state_key]


def test_state_row_label_is_the_display_name() -> None:
    rows = {row["id"].rsplit(":", 1)[-1]: row for row in _state_rows()}
    assert rows["recorded"]["label"] == "Recorded"
    assert rows["settled"]["label"] == "Settled"


def test_state_row_carries_all_status_fields() -> None:
    rows = {row["id"].rsplit(":", 1)[-1]: row for row in _state_rows()}
    attributes = rows["recorded"]["properties"]["attributes"]
    assert attributes == {"code": "recorded", "display_name": "Recorded", "sort_order": 1}
    assert "secret" not in attributes


def test_state_row_validates_against_the_graph_schema() -> None:
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(
        {"schema_version": "1.2", "nodes": _state_rows(), "edges": []}
    )


def test_non_json_status_field_fails_the_row_build() -> None:
    class Opaque:
        pass

    class _OpaqueStateEntity(BaseStateEntity):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        blob: Opaque = Field(description="No JSON form")

    class _OpaqueLifecycle(Lifecycle):
        BAD = _OpaqueStateEntity(code="bad", display_name="Bad", blob=Opaque())
        _template = Lifecycle().state(BAD).initial()

    with pytest.raises(PydanticSerializationError):
        LifeCycleGraphNode(_Host, "status", _OpaqueLifecycle)
