# tests/action_machine/graph/test_entity_field_graph.py
"""
Entity field vertices and ``entity_field`` composition edges on ``EntityGraphNode``.
"""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_field_graph_node import EntityFieldGraphNode
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.domain_model.entities import RelatedCoreEntity, SampleCoreEntity


def test_entity_node_json_omits_nested_fields() -> None:
    node = EntityGraphNode(SampleCoreEntity)
    row = node.to_dict()
    assert row["properties"].keys() == {"description", "entity_kind"}
    assert "fields" not in row["properties"]
    assert "field_order" not in row["properties"]


def test_entity_field_nodes_and_edges_match_scalars() -> None:
    node = EntityGraphNode(SampleCoreEntity)
    names = [e.target_node.label for e in node.entity_field_edges if e.target_node is not None]
    assert names == ["id", "name", "value"]

    for edge in node.entity_field_edges:
        assert edge.edge_name == "entity_field"
        assert edge.is_dag is False
        assert edge.properties["field_name"] == edge.target_node.label

    ordinals = sorted(e.properties["ordinal"] for e in node.entity_field_edges)
    assert ordinals == [0, 1, 2]


def test_entity_field_to_dict_contract() -> None:
    entity_node = EntityGraphNode(SampleCoreEntity)
    field_node = next(e.target_node for e in entity_node.entity_field_edges if e.target_node.label == "id")
    assert isinstance(field_node, EntityFieldGraphNode)
    d = field_node.to_dict()
    assert d["type"] == "EntityField"
    assert d["label"] == "id"
    assert d["properties"]["primary_key_hint"] is True
    assert isinstance(d["properties"]["field_type"], str)


def test_related_entity_excludes_relation_slots_from_entity_field() -> None:
    node = EntityGraphNode(RelatedCoreEntity)
    labels = {e.target_node.label for e in node.entity_field_edges}
    assert labels == {"id", "title"}
    assert "parent" not in labels
    assert "children" not in labels


def test_an_entity_row_without_a_kind_is_rejected() -> None:
    """The schema requires the kind: a row that lost it is a defect, not a tolerant reader's problem."""
    import jsonschema

    node = EntityGraphNode(SampleCoreEntity)
    row = node.to_dict()
    assert row["properties"]["entity_kind"] == "core"

    broken = {**row, "properties": {"description": row["properties"]["description"]}}
    payload = {"schema_version": "1.0", "nodes": [broken], "edges": []}
    with pytest.raises(jsonschema.ValidationError):
        Draft202012Validator(GRAPH_JSON_SCHEMA).validate(payload)


def test_entity_field_export_validates_against_graph_schema() -> None:
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator

    coord = create_node_graph_coordinator()
    payload = json.loads(coord.to_json())
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(payload)

    entity_id = TypeIntrospection.full_qualname(SampleCoreEntity)
    types = {n["id"]: n["type"] for n in payload["nodes"]}
    assert types[entity_id] == "Entity"

    sample_field_edges = [e for e in payload["edges"] if e["type"] == "entity_field" and e["source_id"] == entity_id]
    field_ids = {e["target_id"] for e in sample_field_edges}
    assert field_ids == {f"{entity_id}:{name}" for name in ("id", "name", "value")}

    assert len(sample_field_edges) == 3
    assert {e["properties"]["ordinal"] for e in sample_field_edges} == {0, 1, 2}
    assert all(e["relationship"] == "Composition" for e in sample_field_edges)
    assert all(e["is_dag"] is False for e in sample_field_edges)


class ReferenceShopDomain(BaseDomain):
    """The domain the reference fixtures belong to."""

    name = "reference-shop"
    description = "Reference shop"


@exclude_graph_model
@entity(description="Currency reference value", domain=ReferenceShopDomain)
class ReferenceCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary a field can reference."""

    USD = value(code="usd", display_name="US dollar")


@exclude_graph_model
class EmptyDictionaryEnumEntity(BaseEnumEntity):
    """A base dictionary that declares no values; a field cannot be typed by it."""


@exclude_graph_model
@entity(description="Price tag", domain=ReferenceShopDomain)
class ReferenceTagCoreEntity(BaseCoreEntity):
    """A row with a dictionary reference, an optional one, and a scalar."""

    id: str = Field(description="Tag id")
    currency: ReferenceCurrencyEnumEntity = Field(description="Money unit")
    settlement_currency: ReferenceCurrencyEnumEntity | None = Field(default=None, description="Optional unit")
    note: str = Field(description="Free note")


@exclude_graph_model
@entity(description="Broken tag", domain=ReferenceShopDomain)
class EmptyDictionaryTagCoreEntity(BaseCoreEntity):
    """A row whose field is typed by a dictionary with no values."""

    id: str = Field(description="Tag id")
    currency: EmptyDictionaryEnumEntity = Field(description="Money unit")


def _field_nodes(entity_cls: type) -> dict[str, EntityFieldGraphNode]:
    """Return the entity's field nodes by field name."""
    return {
        edge.target_node.label: edge.target_node
        for edge in EntityGraphNode(entity_cls).entity_field_edges
        if edge.target_node is not None
    }


def test_a_dictionary_typed_field_names_the_dictionary() -> None:
    """A reference is recognizable: the field row points at the dictionary it references."""
    fields = _field_nodes(ReferenceTagCoreEntity)
    expected = TypeIntrospection.full_qualname(ReferenceCurrencyEnumEntity)

    assert fields["currency"].properties["reference_qualname"] == expected
    assert fields["settlement_currency"].properties["reference_qualname"] == expected
    assert "reference_qualname" not in fields["note"].properties


def test_a_reference_field_row_validates_against_the_schema() -> None:
    """The interchange schema declares ``reference_qualname`` on the field row."""
    row = _field_nodes(ReferenceTagCoreEntity)["currency"].to_dict()
    assert row["properties"]["reference_qualname"] == TypeIntrospection.full_qualname(ReferenceCurrencyEnumEntity)

    document = {"schema_version": "1.0", "nodes": [EntityGraphNode(ReferenceTagCoreEntity).to_dict(), row], "edges": []}
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(document)


def test_a_field_typed_by_an_empty_dictionary_is_refused() -> None:
    """A dictionary with no values could never fill the field, so the build refuses it."""
    with pytest.raises(ValueError, match="declares no values; type the field with a concrete dictionary"):
        EntityGraphNode(EmptyDictionaryTagCoreEntity)
