# tests/action_machine/graph/test_resource_domain_removal.py
"""
A resource has no domain, so its node has no ``domain`` edge (protocol 2.0).

``@meta`` on a resource takes no domain: a resource is a database shared by domains, and
its domains are the domains of the entities it lists with ``@entities``. The graph pins
that shape from the outside: the resource node contributes one ``resource_entity`` edge per
listed entity and no other edge, and a built graph carries no ``domain`` edge leaving a
resource.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.graph.nodes.resource_graph_node import ResourceGraphNode
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.isolated_entity_models import run_isolated_model


class _ShopDomain(BaseDomain):
    """The domain of the entity the resource lists."""

    name = "resource_domain_removal"
    description = "Shop"


@entity(description="Customer order", domain=_ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order of the shop database."""

    id: str = Field(description="Order id")


@meta(description="The shop database")
@entities(OrderCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """A database that lists one entity."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


def test_the_resource_node_has_one_resource_entity_edge_and_no_domain_edge() -> None:
    """``get_all_edges`` carries the listed entity and no domain: a resource names no domain."""
    node = ResourceGraphNode(ShopDatabaseStorage)
    (edge,) = node.get_all_edges()

    assert edge.edge_name == "resource_entity"
    assert edge.target_node_id == TypeIntrospection.full_qualname(OrderCoreEntity)
    assert "domain" not in node.to_dict()["properties"]


_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.entity import entity


    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop"


    @entity(description="Customer order", domain=ShopDomain)
    class ShopOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    @meta(description="The shop database")
    @entities(ShopOrderCoreEntity)
    class ShopDatabaseStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls):
            return None


    print(create_node_graph_coordinator().to_json())
    """
)


@pytest.fixture(scope="module")
def built() -> dict[str, Any]:
    """The graph of one resource that lists its entity, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _name(node_id: str) -> str:
    """The class name a node id ends with (a ``__main__`` class has no module prefix)."""
    return node_id.rsplit(".", 1)[-1]


def test_a_built_graph_has_the_resource_node(built: dict[str, Any]) -> None:
    """The resource is in the graph with its description."""
    node = next(node for node in built["nodes"] if node["label"] == "ShopDatabaseStorage")
    assert node["type"] == "Resource"
    assert node["properties"] == {"description": "The shop database"}


def test_a_built_graph_has_no_domain_edge_from_the_resource(built: dict[str, Any]) -> None:
    """No ``domain`` edge leaves a resource; the entity keeps its own domain edge."""
    resource_domain = [
        edge
        for edge in built["edges"]
        if edge["type"] == "domain" and _name(edge["source_id"]) == "ShopDatabaseStorage"
    ]
    assert resource_domain == []

    entity_domain = [
        edge
        for edge in built["edges"]
        if edge["type"] == "domain" and _name(edge["source_id"]) == "ShopOrderCoreEntity"
    ]
    assert len(entity_domain) == 1
    assert _name(entity_domain[0]["target_id"]) == "ShopDomain"


def test_a_built_graph_has_a_resource_entity_edge_to_the_listed_entity(built: dict[str, Any]) -> None:
    """The resource reaches the entity it lists by a ``resource_entity`` aggregation edge."""
    (edge,) = [edge for edge in built["edges"] if edge["type"] == "resource_entity"]
    assert _name(edge["source_id"]) == "ShopDatabaseStorage"
    assert _name(edge["target_id"]) == "ShopOrderCoreEntity"


def test_the_graph_is_protocol_2_0(built: dict[str, Any]) -> None:
    """The graph names 2.0, where a resource reaches its entities through ``resource_entity``."""
    assert built["schema_version"] == "2.0"
