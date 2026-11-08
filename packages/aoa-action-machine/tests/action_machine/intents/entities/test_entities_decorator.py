# tests/action_machine/intents/entities/test_entities_decorator.py
"""
``@entities(*classes)`` — the resource declares the entities of its database.

Covers the valid declaration (ordered tuple, resolver, empty list, every resource kind) and
each refusal: a target that is not a resource, an argument that is not an ``@entity`` and a
class repeated in one declaration. A subclass never inherits its parent's list.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.exceptions import EntitiesDecoratorError
from aoa.action_machine.intents.entities import (
    EntitiesIntentResolver,
    entities,
    entities_info_is_set,
)
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseController, BaseGateway, BaseStorage


class _ShopDomain(BaseDomain):
    """The domain of the entities listed by the test database."""

    name = "shop_entities"
    description = "Shop entities"


@entity(description="Customer order", domain=_ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order of the shop database."""

    id: str = Field(description="Order id")


@entity(description="Customer", domain=_ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    """A customer of the shop database."""

    id: str = Field(description="Customer id")


@meta(description="The shop database")
@entities(OrderCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """A database listing two entities."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


def test_the_declaration_writes_an_ordered_tuple() -> None:
    """``_entities_info`` is a tuple in the order the author wrote, and the resolver reads it."""
    assert ShopDatabaseStorage._entities_info == (OrderCoreEntity, CustomerCoreEntity)
    assert isinstance(ShopDatabaseStorage._entities_info, tuple)
    assert EntitiesIntentResolver.resolve_entities(ShopDatabaseStorage) == (OrderCoreEntity, CustomerCoreEntity)
    assert EntitiesIntentResolver.resolve_entity_names(ShopDatabaseStorage) == ("OrderCoreEntity", "CustomerCoreEntity")


def test_an_empty_list_is_allowed() -> None:
    """A resource that never returns an entity declares an empty list."""
    @meta(description="A database that assembles nothing")
    @entities()
    class _EmptyStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls) -> None:
            return None

    assert _EmptyStorage.__dict__["_entities_info"] == ()
    assert EntitiesIntentResolver.resolve_entities(_EmptyStorage) == ()


def test_a_resource_without_the_declaration_resolves_to_nothing() -> None:
    """The declaration is optional: no ``@entities`` means no listed entity."""
    @meta(description="A resource with no entities")
    class _SilentStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls) -> None:
            return None

    assert entities_info_is_set(_SilentStorage) is False
    assert EntitiesIntentResolver.resolve_entities(_SilentStorage) == ()


def test_a_subclass_does_not_inherit_the_parents_list() -> None:
    """Each resource states what its own database holds; the parent's list is not the child's."""
    @meta(description="A second database")
    class _SecondStorage(ShopDatabaseStorage):
        @classmethod
        def get_wrapper_class(cls) -> None:
            return None

    assert entities_info_is_set(_SecondStorage) is False
    assert EntitiesIntentResolver.resolve_entities(_SecondStorage) == ()


@pytest.mark.parametrize(
    ("base", "name"),
    [
        (BaseStorage, "_KindlessStorage"),
        (BaseGateway, "_KindlessGateway"),
        (BaseController, "_KindlessController"),
    ],
)
def test_every_resource_kind_may_declare_its_entities(base: type, name: str) -> None:
    """The declaration says what the resource may return, not only what a storage holds."""
    cls = type(name, (base,), {"get_wrapper_class": classmethod(lambda _cls: None)})
    declared = entities(OrderCoreEntity, CustomerCoreEntity)(cls)

    assert declared is cls
    assert EntitiesIntentResolver.resolve_entities(cls) == (OrderCoreEntity, CustomerCoreEntity)


def test_a_non_resource_target_is_refused() -> None:
    """``@entities`` applies only to a ``BaseResource`` subclass, naming the refused target."""
    class NotAResource:
        pass

    with pytest.raises(EntitiesDecoratorError, match="BaseResource subclass"):
        entities(OrderCoreEntity)(NotAResource)


def test_a_non_class_target_is_refused() -> None:
    """A non-class target is refused before any attribute is read from it."""
    with pytest.raises(EntitiesDecoratorError, match="applies only to a class"):
        entities(OrderCoreEntity)(object())  # type: ignore[arg-type]


def test_a_non_entity_argument_is_refused() -> None:
    """Every argument is a class decorated with ``@entity``; a plain class is refused by name."""
    class NotAnEntity:
        pass

    with pytest.raises(EntitiesDecoratorError, match=r"NotAnEntity.*is not an @entity"):
        entities(NotAnEntity)


def test_a_non_class_argument_is_refused() -> None:
    """A non-class argument is refused, naming the value's type."""
    with pytest.raises(EntitiesDecoratorError, match="every argument must be a class"):
        entities("OrderCoreEntity")  # type: ignore[arg-type]


def test_a_repeated_class_is_refused() -> None:
    """A database lists each of its entities once; the refusal names the repeated class."""
    with pytest.raises(EntitiesDecoratorError, match=r"OrderCoreEntity.*listed twice"):
        entities(OrderCoreEntity, CustomerCoreEntity, OrderCoreEntity)
