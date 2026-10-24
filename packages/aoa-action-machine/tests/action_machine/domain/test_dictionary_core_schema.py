# tests/action_machine/domain/test_dictionary_core_schema.py
"""
Tests for a field typed by a dictionary: what it accepts, what it refuses, what it serializes.

The field holds a declared value. A declared value and its reference object are
accepted; a bare code, an undeclared code and a constructed copy are refused; the
serialized form is the reference object, and reading is driven by the code.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import Field, ValidationError, field_serializer

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
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

    USD = value(code="usd", display_name="US dollar", symbol="$")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@exclude_graph_model
@entity(description="Dated reference value", domain=CoreSchemaShopDomain)
class SchemaDatedEnumEntity(BaseEnumEntity):
    """A dictionary whose date field carries its own serializer."""

    since: date = Field(description="Start date")
    note: str = Field(description="A plain note")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2), note="plain")

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        """Format the date for consumers."""
        return moment.strftime("%d/%m/%Y")


@exclude_graph_model
@entity(description="Plain dated reference value", domain=CoreSchemaShopDomain)
class SchemaPlainDatedEnumEntity(BaseEnumEntity):
    """A dictionary whose date field has no serializer, so JSON mode chooses the form."""

    since: date = Field(description="Start date")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))


@exclude_graph_model
class SchemaPriceTagCoreEntity(BaseCoreEntity):
    """A plain row that references a currency through the standalone dictionary value schema."""

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


def test_a_field_serializer_reaches_the_reference_form() -> None:
    """The serializer the model declares is what a consumer of the reference sees."""
    reference = SchemaDatedEnumEntity.ITEM.to_reference()

    assert reference["properties"]["since"] == "02/01/2020"
    assert json.loads(SchemaDatedEnumEntity.ITEM.model_dump_json())["properties"]["since"] == "02/01/2020"


def test_a_plain_date_is_emitted_as_its_json_string() -> None:
    """Without a serializer the reference still carries JSON, not a Python date."""
    assert SchemaPlainDatedEnumEntity.ITEM.to_reference()["properties"]["since"] == "2020-01-02"


def test_the_reference_form_is_always_json_serializable() -> None:
    """Every reference can be handed to a JSON writer, which the old getattr loop could not promise."""
    for reference in (
        SchemaDatedEnumEntity.ITEM.to_reference(),
        SchemaPlainDatedEnumEntity.ITEM.to_reference(),
        SchemaCurrencyEnumEntity.EUR.to_reference(),
    ):
        assert json.loads(json.dumps(reference)) == reference


def test_python_mode_may_keep_the_native_value_while_the_reference_does_not() -> None:
    """The reference is the JSON export; `model_dump()` in Python mode is a different contract."""
    assert SchemaPlainDatedEnumEntity.ITEM.model_dump()["properties"]["since"] == date(2020, 1, 2)
    assert isinstance(SchemaPlainDatedEnumEntity.ITEM.to_reference()["properties"]["since"], str)


def test_a_serializer_does_not_bleed_into_the_other_extra_fields() -> None:
    """One field's serializer changes that field only; the neighbour keeps its own emitted form."""
    reference = SchemaDatedEnumEntity.ITEM.to_reference()

    assert reference["properties"] == {"since": "02/01/2020", "note": "plain"}
