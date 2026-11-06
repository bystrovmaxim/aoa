# tests/action_machine/graph/test_one_resource_per_domain_and_data_source.py
"""
A domain reaches a data source through one resource; resources of several domains may share one.

Two resources of ``SalesDomain`` naming ``ShopDataSource`` are refused while the model is built,
naming the domain, the data source and both resources. A resource of ``SalesDomain`` and one of
``BillingDomain`` on ``ShopDataSource`` build. Each model is built in a fresh interpreter.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseStorage, InMemoryDataSource


    class SalesDomain(BaseDomain):
        name = "sales"
        description = "Sales"


    class BillingDomain(BaseDomain):
        name = "billing"
        description = "Billing"


    @meta(description="Shop database")
    class ShopDataSource(InMemoryDataSource):
        pass


    @meta(description="Orders", domain=SalesDomain)
    class OrdersStorage(BaseStorage[ShopDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="Carts", domain={cart_domain})
    class CartStorage(BaseStorage[ShopDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @entity(description="Customer order", resource=OrdersStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    @entity(description="Cart", resource=CartStorage)
    class CartCoreEntity(BaseCoreEntity):
        id: str = Field(description="Cart id")


    try:
        graph = json.loads(create_node_graph_coordinator().to_json())
    except Exception as error:
        print("REFUSE", type(error).__name__, error)
    else:
        print(" ".join(sorted(
            edge["source_id"].rsplit(".", 1)[-1] for edge in graph["edges"] if edge["type"] == "resource_data_source"
        )))
    """
)


def _run(cart_domain: str) -> str:
    result = run_isolated_model(_MODEL.replace("{cart_domain}", cart_domain))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_two_resources_of_one_domain_on_one_data_source_are_refused() -> None:
    assert _run("SalesDomain") == (
        "REFUSE DataSourceDeclarationError SalesDomain reaches ShopDataSource through CartStorage and OrdersStorage: "
        "a domain reaches one data source through one resource."
    )


def test_resources_of_two_domains_share_a_data_source() -> None:
    assert _run("BillingDomain") == "CartStorage OrdersStorage"
