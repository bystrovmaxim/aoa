# tests/action_machine/domain/test_dictionary_core_schema.py
# ruff: noqa: F821  # the class-name alias is the surface this module tests
"""
Tests for a field typed by a dictionary: what it accepts, what it refuses, what it serializes.

The field holds a declared value. A declared value and its reference object are
accepted; a bare code, an undeclared code and a constructed copy are refused; the
serialized form is the reference object, and reading is driven by the code.
"""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class CoreSchemaShopDomain(BaseDomain):
    """The domain these fixtures belong to."""

    name = "core-schema-shop"
    description = "Core schema shop"


@exclude_graph_model
@entity(description="Currency reference value", domain=CoreSchemaShopDomain)
class SchemaCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")

    USD = SchemaCurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")
    EUR = SchemaCurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")


@exclude_graph_model
@entity(description="Price tag", domain=CoreSchemaShopDomain)
class SchemaPriceTagCoreEntity(BaseCoreEntity):
    """A row that references a currency."""

    id: str = Field(description="Tag id")
    amount: float = Field(description="Amount")
    currency: SchemaCurrencyEnumEntity = Field(description="Money unit")
    settlement_currency: SchemaCurrencyEnumEntity | None = Field(default=None, description="Optional unit")


def test_a_declared_value_is_accepted_by_identity() -> None:
    """The field holds the declared object itself."""
    tag = SchemaPriceTagCoreEntity(id="t1", amount=9.99, currency=SchemaCurrencyEnumEntity.EUR)

    assert tag.currency is SchemaCurrencyEnumEntity.EUR


def test_a_reference_object_resolves_by_code() -> None:
    """The wire carries the value whole; its code is what selects the declared value."""
    tag = SchemaPriceTagCoreEntity.model_validate(
        {
            "id": "t2",
            "amount": 1.0,
            "currency": {"code": "usd", "display_name": "Dollar (stale)", "properties": {"symbol": "?"}},
        }
    )

    assert tag.currency is SchemaCurrencyEnumEntity.USD
    assert tag.currency.display_name == "US dollar"


def test_a_bare_code_is_refused() -> None:
    """A code is a storage fact; the resource resolves it before the model sees it."""
    with pytest.raises(ValidationError, match="bare code is not accepted"):
        SchemaPriceTagCoreEntity(id="t3", amount=1.0, currency="eur")


def test_an_undeclared_code_is_refused() -> None:
    """The set is closed, so a code outside it names nothing."""
    with pytest.raises(ValidationError, match="is not a declared value of SchemaCurrencyEnumEntity"):
        SchemaPriceTagCoreEntity(id="t4", amount=1.0, currency={"code": "bootleg"})


def test_a_constructed_copy_is_refused() -> None:
    """A copy of a declared value is not a declared value."""
    copy = SchemaCurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")

    with pytest.raises(ValidationError, match="a copy of a declared value is not a value"):
        SchemaPriceTagCoreEntity(id="t5", amount=1.0, currency=copy)


def test_a_payload_without_a_code_is_malformed() -> None:
    """A reference object without its code cannot be resolved."""
    with pytest.raises(ValidationError, match="needs a non-empty 'code'"):
        SchemaPriceTagCoreEntity(id="t6", amount=1.0, currency={"display_name": "US dollar"})


def test_an_optional_dictionary_field_may_be_absent() -> None:
    """No value is `None`, which is distinct from an unknown code."""
    tag = SchemaPriceTagCoreEntity(id="t7", amount=1.0, currency=SchemaCurrencyEnumEntity.USD)

    assert tag.settlement_currency is None


def test_the_serialized_field_is_the_reference_object() -> None:
    """The row carries the value whole: code, label, and the extra fields under properties."""
    tag = SchemaPriceTagCoreEntity(id="t8", amount=1.0, currency=SchemaCurrencyEnumEntity.EUR)

    assert tag.model_dump()["currency"] == {
        "code": "eur",
        "display_name": "Euro",
        "properties": {"symbol": "€"},
    }


def test_the_value_itself_dumps_as_its_reference_object() -> None:
    """A dictionary value has one wire shape, wherever it is serialized from."""
    assert SchemaCurrencyEnumEntity.USD.model_dump() == {
        "code": "usd",
        "display_name": "US dollar",
        "properties": {"symbol": "$"},
    }


@pytest.mark.parametrize("code", ["usd", "bootleg"])
def test_flat_model_data_cannot_fabricate_a_dictionary_field(code: str) -> None:
    """Only reference-shaped mappings may enter a dictionary field."""
    with pytest.raises(ValidationError, match="reference object"):
        SchemaPriceTagCoreEntity(
            id="flat", amount=1.0,
            currency={"code": code, "display_name": "Forged", "symbol": "?"},
        )
