# tests/action_machine/graph/test_entity_resource_validator.py
"""
Tests for ``validate_entity_resources`` — every link between entities stays inside one resource.

Case 2.4 of issue #469 for every link kind: association, aggregation and composition on
either side, an inverse side, a specialization, a generalization, a dictionary field and a
state type shared through ``Lifecycle[...]``. Each model is built in a fresh interpreter so
a refused declaration never joins the shared model.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
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
        CompositeOne,
        EntityResourceError,
        Generalization,
        Inverse,
        Lifecycle,
        NoInverse,
        Specialization,
        value,
    )
    from aoa.action_machine.graph.validators.entity_resource_validator import validate_entity_resources
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources.base_storage import BaseStorage


    class StoreDomain(BaseDomain):
        name = "store"
        description = "Store"


    @meta(description="Primary relational store", domain=StoreDomain)
    class StorefrontDatabase(BaseStorage):
        pass


    @meta(description="Support desk store", domain=StoreDomain)
    class SupportDatabase(BaseStorage):
        pass


    def probe(*classes):
        try:
            validate_entity_resources(list(classes))
            print("ACCEPT")
        except EntityResourceError as exc:
            print("REFUSE " + str(exc))
    """
)


def _run(body: str) -> str:
    """Run one model in a fresh interpreter and return what it printed."""
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


_ORDER = """
    @entity(description="Customer order", resource=StorefrontDatabase)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
"""


def test_case_2_4_an_association_across_resources_is_refused() -> None:
    """2.4: the message names the field, both entities and both resources."""
    out = _run(
        _ORDER
        + """
    @entity(description="Support ticket", resource=SupportDatabase)
    class SupportTicketCoreEntity(BaseCoreEntity):
        id: str = Field(description="Ticket id")
        order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")

    SupportTicketCoreEntity.model_rebuild()
    probe(SalesOrderCoreEntity, SupportTicketCoreEntity)
    """
    )
    assert out == (
        "REFUSE SupportTicketCoreEntity.order relates SupportTicketCoreEntity (SupportDatabase) "
        "to SalesOrderCoreEntity (StorefrontDatabase): a relation stays inside one resource."
    )


def test_the_same_association_inside_one_resource_is_accepted() -> None:
    """The same link between two entities of one resource builds."""
    out = _run(
        _ORDER
        + """
    @entity(description="Support ticket", resource=StorefrontDatabase)
    class SupportTicketCoreEntity(BaseCoreEntity):
        id: str = Field(description="Ticket id")
        order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")

    SupportTicketCoreEntity.model_rebuild()
    probe(SalesOrderCoreEntity, SupportTicketCoreEntity)
    """
    )
    assert out == "ACCEPT"


_OWNERSHIP = """
    @entity(description="Customer order", resource=StorefrontDatabase)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
        lines: Annotated[{many}[SalesOrderLineDetailEntity], Inverse(field_name="order")] = Field(description="Lines")

    @entity(description="Order line", resource={line_resource})
    class SalesOrderLineDetailEntity(BaseDetailEntity):
        id: str = Field(description="Line id")
        order: Annotated[{one}[SalesOrderCoreEntity], Inverse(field_name="lines")] = Field(description="Order")

    SalesOrderCoreEntity.model_rebuild()
    SalesOrderLineDetailEntity.model_rebuild()
    probe({first}, {second})
"""


def _ownership(many: str, one: str, owner_first: bool) -> str:
    """A two-sided ownership link whose line is stored by the support desk."""
    first, second = ("SalesOrderCoreEntity", "SalesOrderLineDetailEntity")
    if not owner_first:
        first, second = second, first
    return _run(
        _OWNERSHIP.format(many=many, one=one, line_resource="SupportDatabase", first=first, second=second)
    )


def test_a_composition_is_refused_from_the_owner_side() -> None:
    """Composition, judged from the owner: the owner's field is named."""
    out = _ownership("CompositeMany", "AssociationOne", owner_first=True)
    assert out.startswith("REFUSE SalesOrderCoreEntity.lines relates SalesOrderCoreEntity (StorefrontDatabase) ")
    assert out.endswith("to SalesOrderLineDetailEntity (SupportDatabase): a relation stays inside one resource.")


def test_a_composition_is_refused_from_the_other_side() -> None:
    """Composition, judged from the part: the part's field is named."""
    out = _ownership("CompositeMany", "AssociationOne", owner_first=False)
    assert out.startswith("REFUSE SalesOrderLineDetailEntity.order relates SalesOrderLineDetailEntity (SupportDatabase) ")


def test_an_aggregation_is_refused_from_either_side() -> None:
    """Aggregation, judged from each endpoint."""
    assert _ownership("AggregateMany", "AssociationOne", owner_first=True).startswith(
        "REFUSE SalesOrderCoreEntity.lines relates"
    )
    assert _ownership("AggregateMany", "AssociationOne", owner_first=False).startswith(
        "REFUSE SalesOrderLineDetailEntity.order relates"
    )


def test_a_one_sided_aggregation_is_refused() -> None:
    """An aggregation with no inverse is judged from its only side."""
    out = _run(
        _ORDER
        + """
    @entity(description="Order note", resource=SupportDatabase)
    class OrderNoteCoreEntity(BaseCoreEntity):
        id: str = Field(description="Note id")
        order: Annotated[AggregateOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")

    OrderNoteCoreEntity.model_rebuild()
    probe(OrderNoteCoreEntity)
    """
    )
    assert out.startswith("REFUSE OrderNoteCoreEntity.order relates OrderNoteCoreEntity (SupportDatabase) ")


_SPECIALIZATION = """
    @entity(description="Kind of counterparty", resource=StorefrontDatabase)
    class CounterpartyKindEnumEntity(BaseEnumEntity):
        ORGANISATION = value(code="organisation", display_name="Organisation")

    @entity(description="Counterparty", resource=StorefrontDatabase)
    class CounterpartyCoreEntity(BaseCoreEntity):
        id: str = Field(description="Counterparty id")
        details: Annotated[
            Specialization[OrganisationSpecEntity, CounterpartyKindEnumEntity],
            Inverse(field_name="counterparty"),
        ] = Field(description="Variant data")

    @entity(description="Organisation data", resource=SupportDatabase)
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


def test_a_specialization_across_resources_is_refused() -> None:
    """The head's specialization field names an alternative of another resource."""
    out = _run(_SPECIALIZATION + "    probe(CounterpartyCoreEntity)\n")
    assert out == (
        "REFUSE CounterpartyCoreEntity.details relates CounterpartyCoreEntity (StorefrontDatabase) "
        "to OrganisationSpecEntity (SupportDatabase): a relation stays inside one resource."
    )


def test_a_generalization_across_resources_is_refused() -> None:
    """The alternative's generalization field names a head of another resource."""
    out = _run(_SPECIALIZATION + "    probe(OrganisationSpecEntity)\n")
    assert out.startswith(
        "REFUSE OrganisationSpecEntity.counterparty relates OrganisationSpecEntity (SupportDatabase) to "
    )


def test_a_dictionary_field_across_resources_is_refused() -> None:
    """A dictionary is an ordinary entity of its resource."""
    out = _run(
        _ORDER
        + """
    @entity(description="Currency", resource=SupportDatabase)
    class CurrencyEnumEntity(BaseEnumEntity):
        USD = value(code="USD", display_name="US dollar")

    @entity(description="Invoice", resource=StorefrontDatabase)
    class InvoiceCoreEntity(BaseCoreEntity):
        id: str = Field(description="Invoice id")
        currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    InvoiceCoreEntity.model_rebuild()
    probe(InvoiceCoreEntity)
    """
    )
    assert out == (
        "REFUSE InvoiceCoreEntity.currency relates InvoiceCoreEntity (StorefrontDatabase) "
        "to CurrencyEnumEntity (SupportDatabase): a relation stays inside one resource."
    )


_LIFECYCLE = """
    class OrderStateEntity(BaseStateEntity):
        DRAFT = value(code="draft", display_name="Draft")
        PAID = value(code="paid", display_name="Paid")

    class OrderLifecycle(Lifecycle[OrderStateEntity]):
        _template = (
            Lifecycle()
            .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
            .state(OrderStateEntity.PAID).final()
        )

    @entity(description="Customer order", resource=StorefrontDatabase)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
        lifecycle: OrderLifecycle = Field(description="Order status")

    @entity(description="Return", resource={resource})
    class ReturnCoreEntity(BaseCoreEntity):
        id: str = Field(description="Return id")
        lifecycle: OrderLifecycle = Field(description="Return status")

    probe(SalesOrderCoreEntity, ReturnCoreEntity)
"""


def test_a_state_type_shared_across_resources_is_refused() -> None:
    """A state type takes its resource from the entities that use it."""
    out = _run(_LIFECYCLE.format(resource="SupportDatabase"))
    assert out == (
        "REFUSE OrderStateEntity is the state type of SalesOrderCoreEntity.lifecycle (StorefrontDatabase) "
        "and ReturnCoreEntity.lifecycle (SupportDatabase): a lifecycle stays inside one resource."
    )


def test_a_state_type_shared_inside_one_resource_is_accepted() -> None:
    """Two entities of one resource share one state type."""
    assert _run(_LIFECYCLE.format(resource="StorefrontDatabase")) == "ACCEPT"


def test_a_self_relation_is_accepted() -> None:
    """A tree has one resource on both ends."""
    out = _run(
        """
    @entity(description="Category", resource=StorefrontDatabase)
    class CategoryCoreEntity(BaseCoreEntity):
        id: str = Field(description="Category id")
        parent: Annotated[AssociationOne[CategoryCoreEntity] | None, NoInverse()] = Field(
            default=None, description="Parent category"
        )

    CategoryCoreEntity.model_rebuild()
    probe(CategoryCoreEntity)
    """
    )
    assert out == "ACCEPT"
