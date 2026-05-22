# tests/action_machine/graph/test_entity_field_graph.py
"""
Entity field vertices and ``entity_field`` composition edges on ``EntityGraphNode``.
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_field_graph_node import EntityFieldGraphNode
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from tests.action_machine.scenarios.domain_model.entities import RelatedEntity, SampleEntity


def test_entity_node_json_omits_nested_fields() -> None:
    node = EntityGraphNode(SampleEntity)
    row = node.to_dict()
    assert row["properties"].keys() == {"description"}
    assert "fields" not in row["properties"]
    assert "field_order" not in row["properties"]


def test_entity_field_nodes_and_edges_match_scalars() -> None:
    node = EntityGraphNode(SampleEntity)
    names = [e.target_node.label for e in node.entity_field_edges if e.target_node is not None]
    assert names == ["id", "name", "value"]

    for edge in node.entity_field_edges:
        assert edge.edge_name == "entity_field"
        assert edge.is_dag is False
        assert edge.properties["field_name"] == edge.target_node.label

    ordinals = sorted(e.properties["ordinal"] for e in node.entity_field_edges)
    assert ordinals == [0, 1, 2]


def test_entity_field_to_dict_contract() -> None:
    entity_node = EntityGraphNode(SampleEntity)
    field_node = next(e.target_node for e in entity_node.entity_field_edges if e.target_node.label == "id")
    assert isinstance(field_node, EntityFieldGraphNode)
    d = field_node.to_dict()
    assert d["type"] == "EntityField"
    assert d["label"] == "id"
    assert d["properties"]["primary_key_hint"] is True
    assert isinstance(d["properties"]["field_type"], str)


def test_related_entity_excludes_relation_slots_from_entity_field() -> None:
    node = EntityGraphNode(RelatedEntity)
    labels = {e.target_node.label for e in node.entity_field_edges}
    assert labels == {"id", "title"}
    assert "parent" not in labels
    assert "children" not in labels


def test_entity_field_export_validates_against_graph_schema() -> None:
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator

    coord = create_node_graph_coordinator()
    payload = json.loads(coord.to_json())
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(payload)

    entity_id = TypeIntrospection.full_qualname(SampleEntity)
    types = {n["id"]: n["type"] for n in payload["nodes"]}
    assert types[entity_id] == "Entity"

    sample_field_edges = [e for e in payload["edges"] if e["type"] == "entity_field" and e["source_id"] == entity_id]
    field_ids = {e["target_id"] for e in sample_field_edges}
    assert field_ids == {f"{entity_id}:{name}" for name in ("id", "name", "value")}

    assert len(sample_field_edges) == 3
    assert {e["properties"]["ordinal"] for e in sample_field_edges} == {0, 1, 2}
    assert all(e["relationship"] == "Composition" for e in sample_field_edges)
    assert all(e["is_dag"] is False for e in sample_field_edges)
