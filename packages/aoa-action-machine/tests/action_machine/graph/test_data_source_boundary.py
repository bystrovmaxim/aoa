# tests/action_machine/graph/test_data_source_boundary.py
"""
Relations follow the boundary: the data source a resource names, or the resource without one.

Models are declared and built in a fresh interpreter: two resources on one data source
relate their entities; across two data sources, or between a resource with a data source
and one without, the model build refuses. The graph build then checks again, before it
writes a graph, every data source rule a schema cannot: driven with hand-built nodes,
because the class-level passes refuse the same models earlier.
"""

from __future__ import annotations

import textwrap
from typing import Any

import pytest

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator

from ...support.isolated_entity_models import run_isolated_model

_RULE = "a relation stays inside one data source, or inside one resource when there is none."


def _model(support_base: str) -> str:
    """Orders on ``ShopDataSource``; Support on ``support_base``; a ticket associated with an order."""
    billing = (
        '@meta(description="Billing database")\nclass BillingDataSource(BaseDataSource):\n    pass\n'
        if "BillingDataSource" in support_base
        else ""
    )
    return textwrap.dedent(
        f"""
        from typing import Annotated

        from pydantic import Field

        from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDomain, NoInverse
        from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
        from aoa.action_machine.intents.entity import entity
        from aoa.action_machine.intents.meta import meta
        from aoa.action_machine.resources import BaseDataSource, BaseStorage


        class ShopDomain(BaseDomain):
            name = "shop"
            description = "Shop"


        @meta(description="Main shop database")
        class ShopDataSource(BaseDataSource):
            pass


        {{billing}}

        @meta(description="Orders", domain=ShopDomain)
        class OrdersResource(BaseStorage[ShopDataSource]):
            def get_wrapper_class(self):
                return None


        @meta(description="Support", domain=ShopDomain)
        class SupportResource({support_base}):
            def get_wrapper_class(self):
                return None


        @entity(description="Customer order", resource=OrdersResource)
        class SalesOrderCoreEntity(BaseCoreEntity):
            id: str = Field(description="Order id")


        @entity(description="Support ticket", resource=SupportResource)
        class SupportTicketCoreEntity(BaseCoreEntity):
            id: str = Field(description="Ticket id")
            order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="The order it is about")


        try:
            graph = create_node_graph_coordinator().to_json()
        except Exception as error:
            print("REFUSE", error)
        else:
            print("BUILT", "entity_relation" in graph)
        """
    ).replace("{billing}", billing)


def test_two_resources_of_one_data_source_relate_their_entities() -> None:
    """Both resources on ``ShopDataSource``: the model builds, and the relation is in the graph."""
    result = run_isolated_model(_model("BaseStorage[ShopDataSource]"))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "BUILT True"


@pytest.mark.parametrize(
    ("support_base", "named"),
    [("BaseStorage[BillingDataSource]", "SupportResource, BillingDataSource"), ("BaseStorage", "SupportResource, no data source")],
    ids=["another data source", "no data source"],
)
def test_a_relation_outside_one_data_source_is_refused(support_base: str, named: str) -> None:
    """Across two data sources, or to a resource without one, the model build refuses, naming both boundaries."""
    result = run_isolated_model(_model(support_base))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        f"REFUSE SupportTicketCoreEntity.order relates SupportTicketCoreEntity ({named}) "
        f"to SalesOrderCoreEntity (OrdersResource, ShopDataSource): {_RULE}"
    )


# ── Hand-built nodes: the graph build's own data source rules ────────────────────────────


class _Axis:
    """Root type of the harness inspector."""


class _Link(AssociationGraphEdge):
    """A link edge of any name; an ``entity_relation`` carries the field name its id needs."""

    def __init__(self, edge_name: str, target_id: str) -> None:
        super().__init__(edge_name=edge_name, is_dag=False, target_node_id=target_id, target_node=None)

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Serialize with the ``field_name`` an ``entity_relation`` id is built from."""
        properties = {"field_name": "link"} if self.edge_name == "entity_relation" else {}
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": properties,
        }


class _Node(BaseGraphNode[object]):
    """A node with a given type and edges."""

    def __init__(self, node_id: str, node_type: str, edges: list[BaseGraphEdge] | None = None) -> None:
        super().__init__(node_id=node_id, node_type=node_type, label=node_id, properties={}, node_obj=object())
        object.__setattr__(self, "_edges", edges or [])

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """The edges given at construction."""
        return list(self._edges)


class _Inspector(BaseGraphNodeInspector[_Axis]):
    """Contribute a fixed list of nodes."""

    def __init__(self, nodes: list[BaseGraphNode[Any]]) -> None:
        self._nodes = nodes

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """Every node of the harness."""
        return list(self._nodes)

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        """Unused: :meth:`get_graph_nodes` is overridden."""
        return None


_APP = _Node("app.Application", "Application")


def _source(node_id: str, *applications: str) -> _Node:
    """A data source with the given ``application`` edges (one, to the application, by default)."""
    targets = applications or ("app.Application",)
    return _Node(node_id, "DataSource", [_Link("application", target) for target in targets])


def _resource(node_id: str, *sources: str) -> _Node:
    """A resource with the given ``resource_data_source`` edges."""
    return _Node(node_id, "Resource", [_Link("resource_data_source", source) for source in sources])


def _build(*nodes: BaseGraphNode[Any]) -> None:
    NodeGraphCoordinator().build([_Inspector([_APP, *nodes])])


def test_a_resource_with_two_data_sources_is_refused() -> None:
    with pytest.raises(InvalidGraphError) as error:
        _build(_source("d.Shop"), _source("d.Billing"), _resource("r.Orders", "d.Shop", "d.Billing"))
    assert str(error.value) == "Resource r.Orders has 2 resource_data_source edges; a resource has at most one."


def test_a_data_source_edge_to_something_else_is_refused() -> None:
    with pytest.raises(InvalidGraphError) as error:
        _build(_resource("r.Sessions"), _resource("r.Orders", "r.Sessions"))
    assert str(error.value) == "Resource r.Orders has a resource_data_source edge to r.Sessions, which is not a data source."


def test_a_data_source_without_its_application_edge_is_refused() -> None:
    with pytest.raises(InvalidGraphError) as error:
        _build(_Node("d.Shop", "DataSource"), _resource("r.Orders", "d.Shop"))
    assert str(error.value) == "Data source d.Shop has 0 application edges; a data source has exactly one, to the application."


def test_a_data_source_without_a_resource_is_refused() -> None:
    with pytest.raises(InvalidGraphError) as error:
        _build(_source("d.Shop"), _resource("r.Orders"))
    assert str(error.value) == "Data source d.Shop has no resource; a data source is shared by at least one."


def test_the_graph_build_refuses_a_link_across_data_sources() -> None:
    """A link the class-level pass would have refused is refused again before a graph is written."""
    ticket = _Node("e.Ticket", "Entity", [_Link("entity_resource", "r.Support"), _Link("entity_relation", "e.Order")])
    order = _Node("e.Order", "Entity", [_Link("entity_resource", "r.Orders")])
    nodes = (_source("d.Shop"), _source("d.Billing"), _resource("r.Orders", "d.Shop"), _resource("r.Support", "d.Billing"), ticket, order)
    with pytest.raises(InvalidGraphError) as error:
        _build(*nodes)
    assert str(error.value) == f"Edge e.Ticket|entity_relation|link joins e.Ticket (d.Billing) and e.Order (d.Shop): {_RULE}"


def test_the_graph_build_lets_a_link_inside_one_data_source_through() -> None:
    ticket = _Node("e.Ticket", "Entity", [_Link("entity_resource", "r.Support"), _Link("entity_relation", "e.Order")])
    order = _Node("e.Order", "Entity", [_Link("entity_resource", "r.Orders")])
    _build(_source("d.Shop"), _resource("r.Orders", "d.Shop"), _resource("r.Support", "d.Shop"), ticket, order)
