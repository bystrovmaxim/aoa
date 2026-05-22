# tests/action_machine/graph_model/test_field_graph_node_json_schema.py
"""
FieldGraphNode metadata for ``JsonSchemaValue``-annotated result fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures :class:`~aoa.action_machine.graph.nodes.result_graph_node.ResultGraphNode`
companion field nodes expose ``json_schema_value`` / ``json_schema_name`` /
``json_schema`` in interchange ``properties`` and :class:`~aoa.action_machine.graph.nodes.field_graph_node.FieldGraphPayload`,
including optional unions and deep-copy isolation.
"""

from __future__ import annotations

from tests.action_machine.adapters.json_schema_adapter_fixtures import (
    AdapterTestAction,
    GraphJson,
)

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.nodes.result_graph_node import ResultGraphNode
from aoa.action_machine.model.base_result import BaseResult

AdapterTestResult = AdapterTestAction.Result


class OptJsonResult(BaseResult):
    graph: GraphJson | None = None


def test_result_with_json_field_creates_field_node_with_metadata() -> None:
    node = ResultGraphNode(AdapterTestResult)
    field_nodes = node.get_companion_nodes()
    graph_node = next(n for n in field_nodes if n.node_obj.field_name == "graph")
    assert graph_node.properties["json_schema_value"] is True
    assert graph_node.properties["json_schema_name"] == "GraphJson"
    assert graph_node.properties["json_schema"]["type"] == "object"
    assert "nodes" in graph_node.properties["json_schema"]["properties"]


def test_regular_field_has_no_json_schema_metadata() -> None:
    node = ResultGraphNode(AdapterTestResult)
    field_nodes = node.get_companion_nodes()
    domain_node = next(n for n in field_nodes if n.node_obj.field_name == "domain")
    assert domain_node.properties["json_schema_value"] is False
    assert "json_schema_name" not in domain_node.properties
    assert "json_schema" not in domain_node.properties


def test_optional_json_field_detected_correctly() -> None:
    node = ResultGraphNode(OptJsonResult)
    field_nodes = node.get_companion_nodes()
    graph_node = next(n for n in field_nodes if n.node_obj.field_name == "graph")
    assert graph_node.properties["json_schema_value"] is True


def test_json_schema_in_properties_is_deep_copy() -> None:
    node = ResultGraphNode(AdapterTestResult)
    field_nodes = node.get_companion_nodes()
    graph_node = next(n for n in field_nodes if n.node_obj.field_name == "graph")
    schema_in_props = graph_node.properties["json_schema"]
    schema_in_props["injected"] = True  # type: ignore[index]
    assert "injected" not in GraphJson._json_schema


def test_coordinator_build_does_not_raise() -> None:
    coordinator = create_node_graph_coordinator()
    nodes = coordinator.get_all_nodes()
    assert len(nodes) > 0


def test_field_graph_payload_json_schema_not_none() -> None:
    node = ResultGraphNode(AdapterTestResult)
    field_nodes = node.get_companion_nodes()
    graph_node = next(n for n in field_nodes if n.node_obj.field_name == "graph")
    payload = graph_node.node_obj
    assert payload.json_schema_value is True
    assert payload.json_schema is not None
    assert isinstance(payload.json_schema, dict)
