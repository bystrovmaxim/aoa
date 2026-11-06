# tests/action_machine/graph/test_data_source_boundary.py
"""
Relations know no store; the graph build checks every data source rule a schema cannot.

Models are declared and built in a fresh interpreter: two resources relate their entities
whether they share a data source or not. The graph build checks, before it writes a graph,
every data source rule a schema cannot: driven with hand-built nodes.
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


        class SupportDomain(BaseDomain):
            name = "support"
            description = "Support"


        @meta(description="Main shop database")
        class ShopDataSource(BaseDataSource):
            pass


        {{billing}}

        @meta(description="Orders", domain=ShopDomain)
        class OrdersStorage(BaseStorage[ShopDataSource]):
            @classmethod
            def get_wrapper_class(cls):
                return None


        @meta(description="Support", domain=SupportDomain)
        class SupportStorage({support_base}):
            @classmethod
            def get_wrapper_class(cls):
                return None


        @entity(description="Customer order", resource=OrdersStorage)
        class SalesOrderCoreEntity(BaseCoreEntity):
            id: str = Field(description="Order id")


        @entity(description="Support ticket", resource=SupportStorage)
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


def test_two_resources_of_two_data_sources_relate_their_entities() -> None:
    """Support on ``BillingDataSource``: the model builds across the two data sources, and the relation is in the graph."""
    result = run_isolated_model(_model("BaseStorage[BillingDataSource]"))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "BUILT True"


# ── Hand-built nodes: the graph build's own data source rules ────────────────────────────


class _Axis:
    """Root type of the harness inspector."""


class _LinkGraphEdge(AssociationGraphEdge):
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


class _TestGraphNode(BaseGraphNode[object]):
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


_APP = _TestGraphNode("app.Application", "Application")


def _source(node_id: str, *applications: str) -> _TestGraphNode:
    """A data source with the given ``application`` edges (one, to the application, by default)."""
    targets = applications or ("app.Application",)
    return _TestGraphNode(node_id, "DataSource", [_LinkGraphEdge("application", target) for target in targets])


def _resource(node_id: str, *sources: str) -> _TestGraphNode:
    """A resource with the given ``resource_data_source`` edges."""
    return _TestGraphNode(node_id, "Resource", [_LinkGraphEdge("resource_data_source", source) for source in sources])


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
        _build(_TestGraphNode("d.Shop", "DataSource"), _resource("r.Orders", "d.Shop"))
    assert str(error.value) == "Data source d.Shop has 0 application edges; a data source has exactly one, to the application."


def test_a_data_source_without_a_resource_is_refused() -> None:
    with pytest.raises(InvalidGraphError) as error:
        _build(_source("d.Shop"), _resource("r.Orders"))
    assert str(error.value) == "Data source d.Shop has no resource; a data source is shared by at least one."


def test_the_graph_build_lets_a_link_across_data_sources_through() -> None:
    """A link between entities of two data sources is a fact of the logical model."""
    ticket = _TestGraphNode("e.Ticket", "Entity", [_LinkGraphEdge("entity_resource", "r.Support"), _LinkGraphEdge("entity_relation", "e.Order")])
    order = _TestGraphNode("e.Order", "Entity", [_LinkGraphEdge("entity_resource", "r.Orders")])
    _build(_source("d.Shop"), _source("d.Billing"), _resource("r.Orders", "d.Shop"), _resource("r.Support", "d.Billing"), ticket, order)


def test_the_graph_build_lets_a_link_inside_one_data_source_through() -> None:
    ticket = _TestGraphNode("e.Ticket", "Entity", [_LinkGraphEdge("entity_resource", "r.Support"), _LinkGraphEdge("entity_relation", "e.Order")])
    order = _TestGraphNode("e.Order", "Entity", [_LinkGraphEdge("entity_resource", "r.Orders")])
    _build(_source("d.Shop"), _resource("r.Orders", "d.Shop"), _resource("r.Support", "d.Shop"), ticket, order)


def test_the_graph_build_refuses_a_resource_that_stores_an_entity_without_a_data_source() -> None:
    """A resource with an ``entity_resource`` edge into it has exactly one ``resource_data_source`` edge."""
    order = _TestGraphNode("e.Order", "Entity", [_LinkGraphEdge("entity_resource", "r.Orders")])
    line = _TestGraphNode("e.Line", "Entity", [_LinkGraphEdge("entity_resource", "r.Orders")])
    with pytest.raises(InvalidGraphError) as error:
        _build(_resource("r.Orders"), order, line)
    assert str(error.value) == (
        "Resource r.Orders stores e.Line, e.Order and has no resource_data_source edge; a resource that stores an entity has exactly one."
    )


def test_the_graph_build_lets_a_resource_that_stores_nothing_go_without_a_data_source() -> None:
    order = _TestGraphNode("e.Order", "Entity", [_LinkGraphEdge("entity_resource", "r.Orders")])
    _build(_source("d.Shop"), _resource("r.Orders", "d.Shop"), _resource("r.Mail"), order)


def test_the_graph_build_refuses_two_resources_of_one_domain_on_one_data_source() -> None:
    """The graph build checks again that a domain reaches a data source through one resource."""
    domain = _TestGraphNode("dom.Sales", "Domain")
    orders = _TestGraphNode("r.Orders", "Resource", [_LinkGraphEdge("resource_data_source", "d.Shop"), _LinkGraphEdge("domain", "dom.Sales")])
    carts = _TestGraphNode("r.Carts", "Resource", [_LinkGraphEdge("resource_data_source", "d.Shop"), _LinkGraphEdge("domain", "dom.Sales")])
    with pytest.raises(InvalidGraphError) as error:
        _build(domain, _source("d.Shop"), orders, carts)
    assert str(error.value) == (
        "Domain dom.Sales reaches data source d.Shop through resources r.Orders and r.Carts; "
        "a domain reaches one data source through one resource."
    )


def test_the_graph_build_lets_two_domains_share_a_data_source() -> None:
    sales, billing = _TestGraphNode("dom.Sales", "Domain"), _TestGraphNode("dom.Billing", "Domain")
    orders = _TestGraphNode("r.Orders", "Resource", [_LinkGraphEdge("resource_data_source", "d.Shop"), _LinkGraphEdge("domain", "dom.Sales")])
    invoices = _TestGraphNode("r.Invoices", "Resource", [_LinkGraphEdge("resource_data_source", "d.Shop"), _LinkGraphEdge("domain", "dom.Billing")])
    _build(sales, billing, _source("d.Shop"), orders, invoices)
