# tests/action_machine/graph/test_graph_json_schema_values.py
# the class-name alias is the surface this module tests
"""
Tests for the dictionary values on the graph node and in the interchange schema.

An ``enum`` entity row carries its values in ``properties.values``; the schema
requires them for that kind and for no other; the values stay data on the
dictionary node and never become nodes or domain edges of their own.
"""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import Field

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity

_VALIDATOR = Draft202012Validator(GRAPH_JSON_SCHEMA)


class SchemaShopDomain(BaseDomain):
    """The domain the node fixture belongs to."""

    name = "schema-shop"
    description = "Schema shop"


@exclude_graph_model
@entity(description="Edition kind dictionary", domain=SchemaShopDomain)
class EditionKindEnumEntity(BaseEnumEntity):
    """A closed dictionary used to build one entity node."""

    FIRST = value(code="first", display_name="First press")
    REPRESS = value(code="repress", display_name="Repress")


def _document(properties: dict) -> dict:
    """Return a one-node graph document for the given entity properties."""
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "shop.model.EditionKindEnumEntity",
                "type": "Entity",
                "label": "EditionKindEnumEntity",
                "properties": properties,
            }
        ],
        "edges": [],
    }


def test_an_enum_row_with_values_validates() -> None:
    """A dictionary row states its values, and each value carries code, label and properties."""
    _VALIDATOR.validate(
        _document(
            {
                "description": "Edition kind dictionary",
                "entity_kind": "enum",
                "values": [
                    {"code": "first", "display_name": "First press", "properties": {}},
                    {"code": "repress", "display_name": "Repress", "properties": {}},
                ],
            }
        )
    )


def test_an_enum_row_without_values_is_refused() -> None:
    """The values are the dictionary's content; a row without them says nothing."""
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(_document({"description": "Edition kind", "entity_kind": "enum"}))


def test_an_enum_row_with_no_values_is_refused() -> None:
    """An empty list is not a declaration: a closed dictionary declares at least one value."""
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(_document({"description": "Edition kind", "entity_kind": "enum", "values": []}))


def test_a_value_missing_its_label_is_refused() -> None:
    """Each value states its code and its label."""
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(
            _document(
                {
                    "description": "Edition kind",
                    "entity_kind": "enum",
                    "values": [{"code": "first", "properties": {}}],
                }
            )
        )


def test_a_non_dictionary_row_needs_no_values() -> None:
    """Only the dictionary kind declares values; every other kind validates without them."""
    _VALIDATOR.validate(_document({"description": "Order", "entity_kind": "core"}))


def test_the_node_publishes_the_values_and_no_value_node() -> None:
    """The dictionary's node carries its values and has no companion node for them."""
    node = EntityGraphNode(EditionKindEnumEntity)
    row = node.to_dict()

    assert row["type"] == "Entity"
    assert row["properties"]["entity_kind"] == "enum"
    assert row["properties"]["values"] == [
        {"code": "first", "display_name": "First press", "properties": {}},
        {"code": "repress", "display_name": "Repress", "properties": {}},
    ]
    companions = [companion.node_id for companion in node.get_companion_nodes()]
    assert not any(node_id.endswith((":first", ":repress")) for node_id in companions)
    _VALIDATOR.validate(_document(row["properties"]))


def test_a_non_dictionary_node_carries_no_values_key() -> None:
    """A row of another kind does not pretend to declare values."""
    from aoa.action_machine.domain import BaseCoreEntity

    @exclude_graph_model
    @entity(description="Order", domain=SchemaShopDomain)
    class SchemaOrderCoreEntity(BaseCoreEntity):
        """A core entity, kept out of the model graph."""

        id: str = Field(description="Order id")

    assert "values" not in EntityGraphNode(SchemaOrderCoreEntity).to_dict()["properties"]
