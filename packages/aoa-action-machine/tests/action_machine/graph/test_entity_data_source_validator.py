# tests/action_machine/graph/test_entity_data_source_validator.py
"""
Every stored entity has a physical place: the resource that stores it names a data source.

A resource an ``@entity`` names and that names no data source is refused while the model is
built, naming the resource and the entities it stores. A resource that stores nothing may name
none. Each kind AOA gives — in memory, an external service, PostgreSQL — builds, and the graph
has the resource's ``resource_data_source`` edge. Each model is built in a fresh interpreter.
"""

from __future__ import annotations

import textwrap

import pytest

from ...support.isolated_entity_models import run_isolated_model

_HEAD = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseGateway, BaseStorage, ExternalServiceDataSource, InMemoryDataSource
    from aoa.action_machine.resources.postgres import PostgresDataSource, PostgresStorage


    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop"


    def build():
        try:
            graph = json.loads(create_node_graph_coordinator().to_json())
        except Exception as error:
            print("REFUSE", type(error).__name__, error)
        else:
            print(" ".join(sorted(
                f"{edge['source_id'].rsplit('.', 1)[-1]}->{edge['target_id'].rsplit('.', 1)[-1]}"
                for edge in graph["edges"] if edge["type"] == "resource_data_source"
            )))
    """
)


def _run(body: str) -> str:
    """Build one model and its graph in a fresh interpreter and return what it printed."""
    result = run_isolated_model(_HEAD + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_a_resource_that_stores_an_entity_and_names_no_data_source_is_refused() -> None:
    """The message names the resource and every entity it stores."""
    out = _run(
        """
    @meta(description="Orders", domain=ShopDomain)
    class OrdersStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @entity(description="Customer order", resource=OrdersStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    @entity(description="Order line", resource=OrdersStorage)
    class OrderLineCoreEntity(BaseCoreEntity):
        id: str = Field(description="Line id")


    build()
    """
    )
    assert out == (
        "REFUSE EntityResourceError OrdersStorage stores OrderLineCoreEntity, SalesOrderCoreEntity and names no data source: "
        "a resource that stores an entity names its data source as the type argument of its base "
        "(OrdersStorage(<Base>[<Name>DataSource]))."
    )


def test_a_resource_that_stores_nothing_may_name_no_data_source() -> None:
    """A gateway that only calls out stores no entity and needs no data source."""
    out = _run(
        """
    @meta(description="Shop memory")
    class ShopDataSource(InMemoryDataSource):
        pass


    @meta(description="Orders", domain=ShopDomain)
    class OrdersStorage(BaseStorage[ShopDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="Mail sender", domain=ShopDomain)
    class MailGateway(BaseGateway):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @entity(description="Customer order", resource=OrdersStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    build()
    """
    )
    assert out == "OrdersStorage->ShopDataSource"


@pytest.mark.parametrize(
    ("data_source", "resource_base"),
    [
        ("InMemoryDataSource", "BaseStorage"),
        ("ExternalServiceDataSource", "BaseGateway"),
        ("PostgresDataSource", "PostgresStorage"),
    ],
    ids=["in memory", "external service", "PostgreSQL"],
)
def test_every_kind_of_data_source_gives_a_stored_entity_its_place(data_source: str, resource_base: str) -> None:
    """A resource on any kind AOA gives stores entities, and the graph names its data source."""
    resource_name = "OrdersGateway" if resource_base == "BaseGateway" else "OrdersStorage"
    out = _run(
        f"""
    @meta(description="Shop store")
    class ShopDataSource({data_source}):
        pass


    @meta(description="Orders", domain=ShopDomain)
    class {resource_name}({resource_base}[ShopDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @entity(description="Customer order", resource={resource_name})
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    build()
    """
    )
    assert out == f"{resource_name}->ShopDataSource"
