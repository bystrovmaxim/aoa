# packages/aoa-action-machine/tests/action_machine/graph/test_entity_typed_field_graph_edge.py
"""
Every field typed by an entity is linked to it in the graph, as a projection field is.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 7.1 of issue #408. A Result or Params field typed by an entity class — bare,
``| None`` or ``list[...]``, a dictionary included — gets an ``entity_schema``
edge to that entity; a projection field keeps its edge; a field of another type
gets none.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.nodes.params_graph_node import ParamsGraphNode
from aoa.action_machine.graph.nodes.result_graph_node import ResultGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.domain_model.domains import TestStorage


@entity(description="Customer for the graph edge tests", resource=TestStorage)
class EdgeCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Id")


@entity(description="Currencies for the graph edge tests", resource=TestStorage)
class EdgeCurrencyEnumEntity(BaseEnumEntity):
    """A dictionary."""

    EUR = value(code="eur", display_name="Euro")


_WIRE = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"], "additionalProperties": False}


class EdgeResult(BaseResult):
    """Fields of every shape the rule covers, and two it does not."""

    customer: EdgeCustomerCoreEntity = Field(description="Customer")
    maybe: EdgeCustomerCoreEntity | None = Field(default=None, description="Maybe a customer")
    many: list[EdgeCustomerCoreEntity] = Field(default_factory=list, description="Customers")
    currency: EdgeCurrencyEnumEntity = Field(default=EdgeCurrencyEnumEntity.EUR, description="Currency")
    row: EdgeCustomerCoreEntity.schema(schema=_WIRE) = Field(description="Projection")  # type: ignore[valid-type]
    label: str = Field(description="Label")


class EdgeParams(BaseParams):
    """Params typed by an entity."""

    customer: EdgeCustomerCoreEntity = Field(description="Customer")


def _edges(node: BaseGraphNode[Any], field_name: str) -> list[Any]:
    field_node = next(n for n in node.get_companion_nodes() if n.node_id.endswith(f":{field_name}"))
    return [edge for edge in field_node.get_all_edges() if edge.edge_name == "entity_schema"]


@pytest.mark.parametrize(
    ("field_name", "target"),
    [
        ("customer", EdgeCustomerCoreEntity),
        ("maybe", EdgeCustomerCoreEntity),
        ("many", EdgeCustomerCoreEntity),
        ("currency", EdgeCurrencyEnumEntity),
        ("row", EdgeCustomerCoreEntity),
    ],
)
def test_a_result_field_typed_by_an_entity_is_linked_to_it(field_name: str, target: type) -> None:
    """Case 7.1: bare, optional, list, a dictionary and a projection each get one entity_schema edge."""
    edges = _edges(ResultGraphNode(EdgeResult), field_name)
    assert [edge.target_node_id for edge in edges] == [TypeIntrospection.full_qualname(target)]


def test_a_params_field_typed_by_an_entity_is_linked_to_it() -> None:
    """Params follow the same rule."""
    edges = _edges(ParamsGraphNode(EdgeParams), "customer")
    assert [edge.target_node_id for edge in edges] == [TypeIntrospection.full_qualname(EdgeCustomerCoreEntity)]


def test_a_field_of_another_type_has_no_edge() -> None:
    """A string field is not linked to any entity."""
    assert _edges(ResultGraphNode(EdgeResult), "label") == []
