# tests/action_machine/graph/test_dictionary_association_graph.py
"""
Tests for the ordinary association projection of an explicit dictionary selection.

One ``entity_relation`` edge plus one retained ``entity_field`` row describe the field; no
special ``entity_reference`` edge is generated. The edge carries the ordinary association
properties and no inverse identifiers.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    NoInverse,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class GraphDomain(BaseDomain):
    """Domain for dictionary-association graph fixtures."""

    name = "graph-association"
    description = "Graph association"


@entity(description="Currency", domain=GraphDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary a field can select."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")


@exclude_graph_model
@entity(description="Host", domain=GraphDomain)
class HostCoreEntity(BaseCoreEntity):
    """A host selecting a required and an optional dictionary value."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    optional: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Optional currency"
    )


def test_one_ordinary_relation_edge_and_one_retained_field_row() -> None:
    """The dictionary selection projects as one ordinary association edge and one field row."""
    node = EntityGraphNode(HostCoreEntity)

    assert len(node.relations) == 2  # required + optional, same shape
    assert node.references == []
    assert {edge.target_node.label for edge in node.entity_field_edges} == {"id", "currency", "optional"}


def test_the_ordinary_edge_carries_the_association_properties() -> None:
    """Each edge states association, cardinality one and no inverse."""
    node = EntityGraphNode(HostCoreEntity)

    for edge in node.relations:
        assert edge.properties["relation_type"] == "association"
        assert edge.properties["cardinality"] == "one"
        assert edge.properties["has_inverse"] is False
        assert edge.properties["field_name"] in {"currency", "optional"}
        assert "inverse_entity_id" not in edge.properties
        assert "inverse_field" not in edge.properties


def test_the_retained_field_row_names_the_dictionary() -> None:
    """The retained field row's reference_qualname equals the dictionary's graph identifier."""
    node = EntityGraphNode(HostCoreEntity)

    currency_row = next(edge for edge in node.entity_field_edges if edge.target_node.label == "currency")
    assert currency_row.target_node.properties["reference_qualname"] == TypeIntrospection.full_qualname(
        CurrencyEnumEntity
    )
