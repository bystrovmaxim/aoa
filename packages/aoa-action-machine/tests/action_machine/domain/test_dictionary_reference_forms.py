# packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_reference_forms.py
"""
A dictionary reference is accepted on every path and written from a reference computed once.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 4.3–4.5 of issue #407 (4.1 and 4.2 run through the adapters' own tests).
A dictionary relation reads, in every mode, its container, the id object
``{"id": code}`` and the reference object it writes; a to-many relation an array
of them. Each declared value's reference is computed once and every dump gets a
new copy of it.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    AggregateMany,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.resources.base_storage import BaseStorage


class _ReferencesDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "dictionary_reference_forms"
    description = "Entities for the dictionary reference form tests"


@meta(description="Stores the references entities")
class _ReferencesStorage(BaseStorage):
    """Hold the references entities."""


@entity(description="Currencies", domain=_ReferencesDomain)
class RefCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Prices", domain=_ReferencesDomain)
class RefPricesCoreEntity(BaseCoreEntity):
    """An entity with a to-one and a to-many dictionary relation."""

    primary: Annotated[CompositeOne[RefCurrencyEnumEntity], NoInverse()] = Field(description="Primary currency")
    others: Annotated[AggregateMany[RefCurrencyEnumEntity], NoInverse()] = Field(description="Other currencies")


class RefPriceParams(BaseParams):
    """Params with a dictionary relation, as FastAPI and MCP validate them."""

    currency: Annotated[CompositeOne[RefCurrencyEnumEntity], NoInverse()] = Field(description="Currency")


def _prices() -> RefPricesCoreEntity:
    return RefPricesCoreEntity(primary=CompositeOne(id="eur"), others=AggregateMany(ids=("usd",)))


# ── 4.3: a dict in code ─────────────────────────────────────────────────────


def test_a_dict_with_the_id_object_is_accepted_in_code() -> None:
    """Case 4.3: the id object is read in Python mode, as FastAPI and MCP pass it."""
    params = RefPriceParams.model_validate({"currency": {"id": "eur"}})
    assert params.currency.entity is RefCurrencyEnumEntity.EUR
    assert type(params.currency) is CompositeOne


def test_the_container_is_still_accepted() -> None:
    """Case 4.3: the explicit container works as it does today."""
    assert RefPriceParams(currency=CompositeOne(id="eur")).currency.entity is RefCurrencyEnumEntity.EUR


def test_a_to_many_takes_an_array_of_either_object() -> None:
    """A to-many relation reads an array of id objects and references, [] included."""
    prices = RefPricesCoreEntity.model_validate(
        {"primary": {"id": "eur"}, "others": [{"id": "usd"}, {"code": "eur", "display_name": "Euro"}]}
    )
    assert prices.others.entities == (RefCurrencyEnumEntity.USD, RefCurrencyEnumEntity.EUR)
    empty = RefPricesCoreEntity.model_validate({"primary": {"id": "eur"}, "others": []})
    assert empty.others.is_loaded
    assert empty.others.entities == ()


# ── 4.4: out and back in ────────────────────────────────────────────────────


def test_the_reference_written_is_read_back() -> None:
    """Case 4.4: model_dump_json() reads back through model_validate_json and through a dict."""
    prices = _prices()
    assert RefPricesCoreEntity.model_validate_json(prices.model_dump_json()) == prices
    assert RefPricesCoreEntity.model_validate(prices.model_dump(mode="json")) == prices


def test_a_reference_takes_its_label_from_the_catalogue() -> None:
    """Case 4.4: the code selects the value; label and properties come from the catalogue."""
    params = RefPriceParams.model_validate({"currency": {"code": "eur", "display_name": "Dollar"}})
    assert params.currency.entity is RefCurrencyEnumEntity.EUR
    assert params.currency.entity.display_name == "Euro"


def test_the_input_schema_lists_both_objects() -> None:
    """Case 4.4: the validation schema offers the id object and the reference object."""
    currency = RefPriceParams.model_json_schema(mode="validation")["properties"]["currency"]
    shapes = currency["anyOf"]
    assert {tuple(shape["required"]) for shape in shapes} == {("id",), ("code",)}
    others = RefPricesCoreEntity.model_json_schema(mode="validation")["properties"]["others"]
    assert others["type"] == "array"
    assert len(others["items"]["anyOf"]) == 2


def test_the_output_schema_is_the_reference() -> None:
    """The serialization schema still describes the reference written."""
    currency = RefPriceParams.model_json_schema(mode="serialization")["properties"]["currency"]
    assert set(currency["required"]) == {"code", "display_name", "properties"}


# ── refusals ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "currency",
    ["eur", {"id": "eur", "extra": 1}, {"display_name": "Euro"}, {"id": "gbp"}, {"code": ""}, 7],
    ids=["bare-code", "extra-key", "no-code", "unknown-code", "blank-code", "number"],
)
def test_what_is_not_a_reference_is_refused(currency: object) -> None:
    """A bare code, an extra key beside id, a reference without code, an unknown code are refused."""
    with pytest.raises(ValidationError):
        RefPriceParams.model_validate({"currency": currency})


# ── 4.5: a reference computed once ─────────────────────────────────────────


def test_the_json_is_the_reference_byte_for_byte() -> None:
    """Case 4.5: what a relation writes equals the value's to_reference()."""
    dumped = _prices().model_dump(mode="json")
    assert dumped["primary"] == RefCurrencyEnumEntity.EUR.to_reference()
    assert dumped["others"] == [RefCurrencyEnumEntity.USD.to_reference()]


def test_a_reference_is_not_computed_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 4.5: dumping the relation does not dump the declared value again."""
    calls: list[str] = []
    original = RefCurrencyEnumEntity.model_dump

    def counting(self: RefCurrencyEnumEntity, **kwargs: object) -> object:
        calls.append(self.code)
        return original(self, **kwargs)

    monkeypatch.setattr(RefCurrencyEnumEntity, "model_dump", counting)
    prices = _prices()
    for _ in range(3):
        prices.model_dump_json()
        prices.model_dump(mode="json")
    assert calls == []


def test_a_returned_reference_cannot_change_the_catalogue() -> None:
    """Every dump gets a new dict: changing one does not change the next."""
    first = _prices().model_dump(mode="json")
    first["primary"]["display_name"] = "changed"
    first["primary"]["properties"]["symbol"] = "changed"
    second = _prices().model_dump(mode="json")
    assert second["primary"]["display_name"] == "Euro"
    assert second["primary"]["properties"]["symbol"] == "€"
    reference = RefCurrencyEnumEntity.EUR.to_reference()
    reference["properties"]["symbol"] = "changed"
    assert RefCurrencyEnumEntity.EUR.to_reference()["properties"]["symbol"] == "€"
