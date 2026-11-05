# tests/intents/entity/test_entity_resource_decorator.py
"""``@entity(resource=...)``: an entity names the one resource that stores it and takes its domain from it."""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityDecoratorError
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_gateway import BaseGateway
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.base_storage import BaseStorage


class StoreDomain(BaseDomain):
    """The shop's bounded context."""

    name = "store"
    description = "Store"


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabase(BaseStorage):
    """Hold the store's rows."""


@meta(description="Session cache", domain=StoreDomain)
class StorefrontSessionCache(BaseStorage):
    """Hold the store's sessions."""


@meta(description="Payment provider", domain=StoreDomain)
class PaymentGateway(BaseGateway):
    """Talk to the payment provider."""


@meta(description="Checkout scheduler", domain=StoreDomain)
class CheckoutController(BaseController):
    """Run checkout jobs."""


class NoMetaDatabase(BaseStorage):
    """A storage that declares no domain."""


def _declare(**kwargs: object) -> type:
    """Declare ``SalesOrderCoreEntity`` with the given ``@entity`` keywords."""

    @entity(description="Customer order", **kwargs)  # type: ignore[arg-type]
    class SalesOrderCoreEntity(BaseCoreEntity):
        """A customer's order."""

        id: str = Field(description="Order id")

    return SalesOrderCoreEntity


def test_case_2_6_the_domain_comes_from_the_resource() -> None:
    """2.6: the entity is accepted, stored by the resource, in the resource's domain."""
    order = _declare(resource=StorefrontDatabase)
    assert EntityIntentResolver.resolve_resource_type(order) is StorefrontDatabase
    assert EntityIntentResolver.resolve_domain_type(order) is StoreDomain
    assert "domain" not in order._entity_info


@pytest.mark.parametrize("resource", [StorefrontDatabase, PaymentGateway, CheckoutController])
def test_any_kind_of_resource_stores_an_entity(resource: type[BaseResource]) -> None:
    """A storage, a gateway and a controller each own entities."""
    assert EntityIntentResolver.resolve_resource_type(_declare(resource=resource)) is resource


def test_case_2_1_the_resource_is_required() -> None:
    """2.1: no resource is refused, naming the entity."""
    with pytest.raises(EntityDecoratorError) as error:
        _declare()
    assert str(error.value) == "SalesOrderCoreEntity — @entity needs resource=: an entity is stored by a resource."


def test_case_2_2_domain_is_not_a_parameter() -> None:
    """2.2: ``domain=`` is refused by the signature itself."""
    with pytest.raises(TypeError, match="unexpected keyword argument 'domain'"):
        entity(description="Customer order", domain=StoreDomain, resource=StorefrontDatabase)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("given", "message"),
    [
        (StoreDomain, "SalesOrderCoreEntity — @entity resource= must be a BaseResource subclass, got StoreDomain."),
        ("StorefrontDatabase", "SalesOrderCoreEntity — @entity resource= must be a BaseResource subclass, got 'StorefrontDatabase'."),
        (
            BaseStorage,
            "SalesOrderCoreEntity — @entity resource= must be a concrete resource, got BaseStorage, "
            "which is excluded from the graph model.",
        ),
        (
            BaseResource,
            "SalesOrderCoreEntity — @entity resource= must be a concrete resource, got BaseResource, "
            "which is excluded from the graph model.",
        ),
        (
            NoMetaDatabase,
            "SalesOrderCoreEntity — @entity resource= NoMetaDatabase declares no domain: decorate it with @meta(domain=...).",
        ),
    ],
)
def test_case_2_3_the_resource_must_be_a_resource(given: object, message: str) -> None:
    """2.3: anything but a concrete resource with a domain is refused, naming the entity and what was given."""
    with pytest.raises(EntityDecoratorError) as error:
        _declare(resource=given)
    assert str(error.value) == message


def test_case_2_3_an_action_is_not_a_resource() -> None:
    """2.3: an action class is refused like any other non-resource."""
    from aoa.action_machine.model import BaseAction

    with pytest.raises(EntityDecoratorError, match=r"must be a BaseResource subclass, got BaseAction\."):
        _declare(resource=BaseAction)


def test_case_2_5_one_resource_only() -> None:
    """2.5: several resources are refused, naming every one."""
    with pytest.raises(EntityDecoratorError) as error:
        _declare(resource=(StorefrontDatabase, StorefrontSessionCache))
    assert str(error.value) == (
        "SalesOrderCoreEntity — @entity takes one resource, got 2: StorefrontDatabase, StorefrontSessionCache."
    )


def test_a_subclass_without_its_own_entity_inherits_the_resource() -> None:
    """A subclass with no ``@entity`` of its own inherits its parent's declaration, resource included."""
    order = _declare(resource=StorefrontDatabase)

    class RushOrderCoreEntity(order):  # type: ignore[misc, valid-type]
        """A rush order."""

    assert EntityIntentResolver.resolve_resource_type(RushOrderCoreEntity) is StorefrontDatabase
