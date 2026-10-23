# tests/action_machine/domain/test_dictionary_scope.py
# the class-name alias is the surface this module tests
"""
Tests for the dictionary kind's closed set: its values, its catalogue and its refusals.

Covers the declaration surface of a dictionary, the reference form the graph and
the wire carry, the non-inheritance of values, and the two declaration mistakes:
duplicate codes and a concrete dictionary without values.

The fixtures derive from the dictionary kind but are kept out of the model graph,
so no other suite sees an extra entity node.
"""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """The domain these fixtures belong to."""

    name = "shop"
    description = "Shop model"


@exclude_graph_model
@entity(description="Currency reference value", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary with two values and one extra field."""

    symbol: str = Field(description="Currency symbol")

    USD = value(code="usd", display_name="US dollar", symbol="$")
    EUR = value(code="eur", display_name="Euro", symbol="€")


def test_the_kind_supplies_exactly_two_fields() -> None:
    """A dictionary value carries its code and its label; everything else is the model's."""
    assert set(BaseEnumEntity.model_fields) == {"code", "display_name"}
    assert set(CurrencyEnumEntity.model_fields) == {"code", "display_name", "symbol"}


def test_the_catalogue_keeps_declaration_order() -> None:
    """Values are reported in the order they were declared, and by_code finds each one."""
    assert CurrencyEnumEntity.codes() == ["usd", "eur"]
    assert CurrencyEnumEntity.members == (CurrencyEnumEntity.USD, CurrencyEnumEntity.EUR)
    assert CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR
    assert CurrencyEnumEntity.entity_type is CurrencyEnumEntity


def test_a_value_carries_its_reference_form() -> None:
    """The graph and the wire read the same shape: code, label, and the extra fields under properties."""
    assert CurrencyEnumEntity.USD.to_reference() == {
        "code": "usd",
        "display_name": "US dollar",
        "properties": {"symbol": "$"},
    }


def test_values_are_not_inherited() -> None:
    """A subclass declares its own set and carries none of the parent's values."""

    @exclude_graph_model
    @entity(description="Fiat currencies", domain=ShopDomain)
    class FiatCurrencyEnumEntity(CurrencyEnumEntity):
        """A different dictionary that reuses the fields."""

        GBP = value(code="gbp", display_name="Pound sterling", symbol="£")

    assert FiatCurrencyEnumEntity.codes() == ["gbp"]
    with pytest.raises(KeyError):
        FiatCurrencyEnumEntity.by_code("usd")


def test_a_decorated_dictionary_without_values_is_refused() -> None:
    """The set is closed, so a concrete dictionary states every value it has."""
    with pytest.raises(ValueError, match="declares no values; a closed dictionary states its values"):

        @entity(description="Empty dictionary", domain=ShopDomain)
        class NothingEnumEntity(BaseEnumEntity):
            """Declare nothing."""


def test_an_intermediate_class_without_values_is_accepted() -> None:
    """A base for dictionaries is not a dictionary."""

    @exclude_graph_model
    class AbstractMoneyEnumEntity(BaseEnumEntity):
        """Share a field among dictionaries; declare no values."""

        symbol: str = Field(description="Currency symbol")

    assert AbstractMoneyEnumEntity.members == ()


def test_duplicate_codes_are_refused() -> None:
    """One code identifies one value."""
    with pytest.raises(ValueError, match="duplicate value code"):

        @exclude_graph_model
        @entity(description="Duplicate codes", domain=ShopDomain)
        class DuplicateEnumEntity(BaseEnumEntity):
            """Declare the same code twice."""

            ONE = value(code="same", display_name="One")
            TWO = value(code="same", display_name="Two")


def test_a_blank_code_or_label_is_refused() -> None:
    """A value's identity and label are non-empty after strip."""
    with pytest.raises(ValidationError, match="cannot be empty or whitespace-only"):
        CurrencyEnumEntity(code="  ", display_name="Blank code", symbol="$")
    with pytest.raises(ValidationError, match="cannot be empty or whitespace-only"):
        CurrencyEnumEntity(code="x", display_name=" ", symbol="$")


def test_a_child_without_extra_fields_constructs_its_own_values() -> None:
    """A parent's catalogue cannot intercept a child's declarations."""
    @exclude_graph_model
    class ParentEnumEntity(BaseEnumEntity):
        """Declare the parent vocabulary."""
        OLD = value(code="old", display_name="Old")

    @exclude_graph_model
    class ChildEnumEntity(ParentEnumEntity):
        """Declare a separate vocabulary using the same fields."""
        NEW = value(code="new", display_name="New")

    assert ChildEnumEntity.codes() == ["new"]
    assert ChildEnumEntity.NEW.code == "new"
    assert type(ChildEnumEntity.NEW) is ChildEnumEntity
    assert ParentEnumEntity.codes() == ["old"]
