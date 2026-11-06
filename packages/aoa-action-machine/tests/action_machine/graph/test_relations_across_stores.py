# tests/action_machine/graph/test_relations_across_stores.py
"""
A link between entities is a fact of the logical model: it joins entities of any resources and data sources.

Every link kind is declared between an entity of ``StorefrontStorage`` (``StorefrontDataSource``) and one of
``SupportStorage`` (``SupportDataSource``) — association, aggregation and composition from either side, an
inverse side, a specialization, a generalization, a dictionary field and a state type shared through
``Lifecycle[...]`` — and the model and its graph build with the link in them. Each model is built in a fresh
interpreter so a declaration never joins the shared model.
"""

from __future__ import annotations

import textwrap

import pytest

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    import json
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AggregateMany,
        AggregateOne,
        AssociationOne,
        BaseCoreEntity,
        BaseDetailEntity,
        BaseDomain,
        BaseEnumEntity,
        BaseSpecEntity,
        BaseStateEntity,
        Classifier,
        CompositeMany,
        Generalization,
        Inverse,
        Lifecycle,
        NoInverse,
        Specialization,
        value,
    )
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseDataSource, BaseStorage


    class StoreDomain(BaseDomain):
        name = "store"
        description = "Store"


    class SupportDomain(BaseDomain):
        name = "support"
        description = "Support"


    @meta(description="Storefront database")
    class StorefrontDataSource(BaseDataSource):
        pass


    @meta(description="Support desk database")
    class SupportDataSource(BaseDataSource):
        pass


    @meta(description="Primary relational store", domain=StoreDomain)
    class StorefrontStorage(BaseStorage[StorefrontDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="Support desk store", domain=SupportDomain)
    class SupportStorage(BaseStorage[SupportDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    def edges(edge_type):
        graph = json.loads(create_node_graph_coordinator().to_json())
        found = sorted(
            f"{edge['source_id'].rsplit('.', 1)[-1]}->{edge['target_id'].rsplit('.', 1)[-1]}"
            for edge in graph["edges"]
            if edge["type"] == edge_type
        )
        print(" ".join(found))
    """
)


def _run(body: str) -> str:
    """Build one model and its graph in a fresh interpreter and return what it printed."""
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


_ORDER = """
    @entity(description="Customer order", resource=StorefrontStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
"""


def test_an_association_across_data_sources_builds() -> None:
    """A ticket of the support desk points at an order of the storefront: the graph has the relation."""
    out = _run(
        _ORDER
        + """
    @entity(description="Support ticket", resource=SupportStorage)
    class SupportTicketCoreEntity(BaseCoreEntity):
        id: str = Field(description="Ticket id")
        order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")

    SupportTicketCoreEntity.model_rebuild()
    edges("entity_relation")
    """
    )
    assert out == "SupportTicketCoreEntity->SalesOrderCoreEntity"


_OWNERSHIP = """
    @entity(description="Customer order", resource=StorefrontStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
        lines: Annotated[{many}[SalesOrderLineDetailEntity], Inverse(field_name="order")] = Field(description="Lines")

    @entity(description="Order line", resource=SupportStorage)
    class SalesOrderLineDetailEntity(BaseDetailEntity):
        id: str = Field(description="Line id")
        order: Annotated[AssociationOne[SalesOrderCoreEntity], Inverse(field_name="lines")] = Field(description="Order")

    SalesOrderCoreEntity.model_rebuild()
    SalesOrderLineDetailEntity.model_rebuild()
    edges("entity_relation")
"""


@pytest.mark.parametrize("many", ["CompositeMany", "AggregateMany"])
def test_an_ownership_with_its_inverse_side_across_data_sources_builds(many: str) -> None:
    """A composition or an aggregation, both sides declared, joins the two data sources from either end."""
    out = _run(_OWNERSHIP.format(many=many))
    assert out == "SalesOrderCoreEntity->SalesOrderLineDetailEntity SalesOrderLineDetailEntity->SalesOrderCoreEntity"


def test_a_one_sided_aggregation_across_data_sources_builds() -> None:
    """An aggregation with no inverse joins the two data sources from its only side."""
    out = _run(
        _ORDER
        + """
    @entity(description="Order note", resource=SupportStorage)
    class OrderNoteCoreEntity(BaseCoreEntity):
        id: str = Field(description="Note id")
        order: Annotated[AggregateOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")

    OrderNoteCoreEntity.model_rebuild()
    edges("entity_relation")
    """
    )
    assert out == "OrderNoteCoreEntity->SalesOrderCoreEntity"


_SPECIALIZATION = """
    @entity(description="Kind of counterparty", resource=StorefrontStorage)
    class CounterpartyKindEnumEntity(BaseEnumEntity):
        ORGANISATION = value(code="organisation", display_name="Organisation")

    @entity(description="Counterparty", resource=StorefrontStorage)
    class CounterpartyCoreEntity(BaseCoreEntity):
        id: str = Field(description="Counterparty id")
        details: Annotated[
            Specialization[OrganisationSpecEntity, CounterpartyKindEnumEntity],
            Inverse(field_name="counterparty"),
        ] = Field(description="Variant data")

    @entity(description="Organisation data", resource=SupportStorage)
    class OrganisationSpecEntity(BaseSpecEntity):
        id: str = Field(description="Head id")
        counterparty: Annotated[
            Generalization[CounterpartyCoreEntity],
            Classifier(variant=CounterpartyKindEnumEntity.ORGANISATION),
            Inverse(CounterpartyCoreEntity, "details"),
        ] = Field(description="Common data")

    CounterpartyCoreEntity.model_rebuild()
    OrganisationSpecEntity.model_rebuild()
"""


def test_a_specialization_across_data_sources_builds() -> None:
    """The head names an alternative of the other data source."""
    assert _run(_SPECIALIZATION + '    edges("entity_specialization")\n') == "CounterpartyCoreEntity->OrganisationSpecEntity"


def test_a_generalization_across_data_sources_builds() -> None:
    """The alternative names a head of the other data source."""
    assert _run(_SPECIALIZATION + '    edges("parent_entity")\n') == "OrganisationSpecEntity->CounterpartyCoreEntity"


def test_a_dictionary_field_across_data_sources_builds() -> None:
    """A dictionary of the support desk names the currency of a storefront invoice."""
    out = _run(
        """
    @entity(description="Currency", resource=SupportStorage)
    class CurrencyEnumEntity(BaseEnumEntity):
        USD = value(code="USD", display_name="US dollar")

    @entity(description="Invoice", resource=StorefrontStorage)
    class InvoiceCoreEntity(BaseCoreEntity):
        id: str = Field(description="Invoice id")
        currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    InvoiceCoreEntity.model_rebuild()
    edges("entity_relation")
    """
    )
    assert out == "InvoiceCoreEntity->CurrencyEnumEntity"


def test_a_state_type_shared_across_data_sources_builds() -> None:
    """An order and a return of two data sources share one state type: each carries its lifecycle."""
    out = _run(
        """
    class OrderStateEntity(BaseStateEntity):
        DRAFT = value(code="draft", display_name="Draft")
        PAID = value(code="paid", display_name="Paid")

    class OrderLifecycle(Lifecycle[OrderStateEntity]):
        _template = (
            Lifecycle()
            .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
            .state(OrderStateEntity.PAID).final()
        )

    @entity(description="Customer order", resource=StorefrontStorage)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
        lifecycle: OrderLifecycle = Field(description="Order status")

    @entity(description="Return", resource=SupportStorage)
    class ReturnCoreEntity(BaseCoreEntity):
        id: str = Field(description="Return id")
        lifecycle: OrderLifecycle = Field(description="Return status")

    edges("lifecycle")
    """
    )
    assert out == "ReturnCoreEntity->ReturnCoreEntity:lifecycle:lifecycle SalesOrderCoreEntity->SalesOrderCoreEntity:lifecycle:lifecycle"
