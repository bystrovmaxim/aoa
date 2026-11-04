# packages/aoa-action-machine/tests/action_machine/domain/test_relation_container_protocols.py
"""
A relation container never passes itself off as the entity it holds.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 1.1, 1.2, 1.4 and 1.5 of issue #405. A container forwards ordinary names
to its loaded entity, but never Python's or Pydantic's protocol names, so a dump
treats it as a container and a copy or a pickle gives a container back.
"""

from __future__ import annotations

import copy
import pickle
from typing import Annotated

import pytest
from pydantic import Field
from pydantic_core import PydanticSerializationError

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.domain.exceptions import RelationNotLoadedError
from aoa.action_machine.intents.entity import entity


class _ProtocolsDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "relation_protocols"
    description = "Entities for the relation container protocol tests"


@entity(description="Customer", domain=_ProtocolsDomain)
class ProtocolCustomerCoreEntity(BaseCoreEntity):
    """A customer an order points at."""

    id: str = Field(description="Customer id")
    name: str = Field(description="Name")

    def _label(self) -> str:
        """Return the customer's name, from a method whose name starts with one underscore."""
        return self.name


@entity(description="Order", domain=_ProtocolsDomain)
class ProtocolOrderCoreEntity(BaseCoreEntity):
    """An order with one relation to its customer."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[ProtocolCustomerCoreEntity], NoInverse()] = Field(description="Customer")


@entity(description="Currencies", domain=_ProtocolsDomain)
class ProtocolCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="Prices", domain=_ProtocolsDomain)
class ProtocolPricesCoreEntity(BaseCoreEntity):
    """An entity with a dictionary reference."""

    primary: Annotated[CompositeOne[ProtocolCurrencyEnumEntity], NoInverse()] = Field(description="Primary currency")


def _loaded() -> AssociationOne[ProtocolCustomerCoreEntity]:
    return AssociationOne[ProtocolCustomerCoreEntity](id="c1", entity=ProtocolCustomerCoreEntity(id="c1", name="Ann"))


def _order() -> ProtocolOrderCoreEntity:
    return ProtocolOrderCoreEntity(id="o1", customer=_loaded())


# ── 1.1 and 1.2: dumps ──────────────────────────────────────────────────────


def test_json_dump_of_a_loaded_relation_is_never_an_empty_object() -> None:
    """Case 1.1: the container has no JSON form yet, so the dump says so instead of writing {}."""
    with pytest.raises(PydanticSerializationError, match="AssociationOne"):
        _order().model_dump(mode="json")


def test_python_dump_of_a_dictionary_reference_keeps_the_container() -> None:
    """Case 1.2: Python-mode model_dump returns the container."""
    dumped = ProtocolPricesCoreEntity(primary=CompositeOne(id="eur")).model_dump()
    assert isinstance(dumped["primary"], CompositeOne)
    assert dumped["primary"].entity is ProtocolCurrencyEnumEntity.EUR


# ── forwarding ──────────────────────────────────────────────────────────────


def test_a_protocol_name_is_not_forwarded() -> None:
    """A name that starts and ends with two underscores raises AttributeError."""
    with pytest.raises(AttributeError):
        _ = _loaded().__pydantic_serializer__


def test_an_ordinary_name_is_still_forwarded() -> None:
    """order.customer.name still reads the customer's name."""
    assert _order().customer.name == "Ann"


def test_a_name_with_one_leading_underscore_is_still_forwarded() -> None:
    """Only names with two underscores on both sides stop."""
    assert _loaded()._label() == "Ann"


def test_an_unloaded_relation_still_refuses_an_ordinary_name() -> None:
    """An ordinary name on an unloaded container raises RelationNotLoadedError."""
    with pytest.raises(RelationNotLoadedError):
        _ = AssociationOne[ProtocolCustomerCoreEntity](id="c9").name


# ── 1.4 and 1.5: copies and pickles ─────────────────────────────────────────


def test_a_deep_copy_of_a_loaded_relation_is_a_container() -> None:
    """Case 1.4: deepcopy keeps the class and the id and copies the entity."""
    loaded = _loaded()
    copied = copy.deepcopy(loaded)
    assert type(copied) is AssociationOne
    assert copied.id == "c1"
    assert copied.entity == loaded.entity
    assert copied.entity is not loaded.entity


def test_a_deep_copy_of_an_entity_keeps_its_relation() -> None:
    """Case 1.4: model_copy(deep=True) of the order holds a container, not the customer."""
    customer = _order().model_copy(deep=True).customer
    assert type(customer) is AssociationOne
    assert customer.name == "Ann"


def test_a_deep_copy_of_a_many_relation_keeps_its_state() -> None:
    """Case 1.4: a Many container keeps its ids, entities and loaded state."""
    many = AssociationMany[ProtocolCustomerCoreEntity](
        ids=("c1",), entities=(ProtocolCustomerCoreEntity(id="c1", name="Ann"),)
    )
    copied = copy.deepcopy(many)
    assert type(copied) is AssociationMany
    assert copied.ids == ("c1",)
    assert copied.is_loaded
    assert copied.entities == many.entities


@pytest.mark.parametrize(
    "container",
    [
        _loaded(),
        AssociationOne[ProtocolCustomerCoreEntity](id="c9"),
        AssociationMany[ProtocolCustomerCoreEntity](ids=("c1", "c2")),
        AssociationMany[ProtocolCustomerCoreEntity](ids=(), entities=(), entities_loaded=True),
    ],
    ids=["one-loaded", "one-unloaded", "many-unloaded", "many-loaded-empty"],
)
@pytest.mark.parametrize(
    "how",
    [copy.copy, copy.deepcopy, lambda c: pickle.loads(pickle.dumps(c))],
    ids=["copy", "deepcopy", "pickle"],
)
def test_a_container_copies_and_pickles_as_a_frozen_container(container, how) -> None:  # type: ignore[no-untyped-def]
    """Case 1.5: copy, deepcopy and pickle give an equal container that still refuses assignment."""
    result = how(container)
    assert type(result) is type(container)
    assert result == container
    assert result.is_loaded == container.is_loaded
    with pytest.raises(AttributeError):
        result.foo = 1
