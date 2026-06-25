# tests/action_machine/graph/test_depends_graph_edge_mode.py
"""PR-3 / PR-5: ``mode`` on ``DependsGraphEdge`` / JSON Schema (wiring: scenarios layer)."""

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from aoa.action_machine.graph.edges.depends_graph_edge import DependsGraphEdge
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.intents.depends import UseCase
from tests.support.domain_model.depends_mode_host_action import DependsModeHostAction


def test_get_dependency_edges_includes_mode_in_properties() -> None:
    edges = DependsGraphEdge.get_dependency_edges(DependsModeHostAction)
    assert len(edges) == 2
    by_suffix = {e.target_node_id.rsplit(".", 1)[-1]: e for e in edges}
    assert by_suffix["PingAction"].properties["mode"] == UseCase.include
    assert by_suffix["PaymentServiceResource"].properties.get("mode") is None


def test_depends_graph_edge_to_dict_serializes_mode_when_valid() -> None:
    edge = DependsGraphEdge(
        target_node_id="pkg.PingAction",
        description="d",
        factory=None,
        mode=UseCase.extend,
    )
    row = edge.to_dict(source_id="pkg.Host")
    assert row["properties"]["description"] == "d"
    assert row["properties"]["mode"] == "extend"


def test_depends_graph_edge_to_dict_omits_mode_when_none() -> None:
    edge = DependsGraphEdge(
        target_node_id="pkg.Svc",
        description="d",
        factory=None,
        mode=None,
    )
    row = edge.to_dict(source_id="pkg.Host")
    assert row["properties"] == {"description": "d"}
    assert "mode" not in row["properties"]


def _minimal_graph_doc(*, mode: str | None) -> dict:
    props: dict[str, str] = {"description": "dep"}
    if mode is not None:
        props["mode"] = mode
    return {
        "schema_version": "1.0",
        "nodes": [
            {"id": "a", "type": "Action", "label": "A", "properties": {"description": "host"}},
            {"id": "b", "type": "Resource", "label": "B", "properties": {"description": "tgt"}},
        ],
        "edges": [
            {
                "source_id": "a",
                "target_id": "b",
                "type": "@depends",
                "relationship": "Association",
                "is_dag": True,
                "properties": props,
            },
        ],
    }


def test_graph_json_schema_accepts_depends_edge_with_mode_include() -> None:
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(_minimal_graph_doc(mode="include"))


def test_graph_json_schema_accepts_depends_edge_without_mode() -> None:
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(_minimal_graph_doc(mode=None))


def test_graph_json_schema_rejects_depends_edge_with_invalid_mode() -> None:
    with pytest.raises(ValidationError):
        Draft202012Validator(GRAPH_JSON_SCHEMA).validate(_minimal_graph_doc(mode="nope"))
