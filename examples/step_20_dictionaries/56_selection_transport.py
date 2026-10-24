"""Select canonical dictionary values in Python and JSON, then export references.
Run: .venv/bin/python examples/step_20_dictionaries/56_selection_transport.py
"""

from typing import Annotated

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class SelectionDomain(BaseDomain):
    """Group the selection declarations."""

    name = "selection"
    description = "Dictionary selection transport"


@entity(description="Currency", domain=SelectionDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shared currency values."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="Price selection", domain=SelectionDomain)
class PriceCoreEntity(BaseCoreEntity):
    """Require a selection while permitting explicit absence."""

    currency: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(description="Currency")


def python_selection() -> None:
    """Resolve a wrapper to the canonical shared member."""
    original = AssociationOne(id="eur")
    price = PriceCoreEntity(currency=original)
    assert price.currency is not original
    assert price.currency.entity is CurrencyEnumEntity.EUR
    assert price.currency.is_loaded and original.entity is None
    print("Python selection:", price.currency.id, price.currency.symbol)
    try:
        PriceCoreEntity(currency=CurrencyEnumEntity.EUR)
    except ValidationError as error:
        assert error.errors()[0]["type"] == "is_instance_of"
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A raw member was accepted")


def json_selection() -> None:
    """Use the JSON input shape and explicit nullability."""
    price = PriceCoreEntity.model_validate_json('{"currency":{"id":"eur"}}')
    assert price.currency.entity is CurrencyEnumEntity.EUR
    assert PriceCoreEntity.model_validate_json('{"currency":null}').currency is None
    payload = price.model_dump(mode="json")
    assert payload == {"currency": {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}}
    print("JSON export:", payload)
    try:
        PriceCoreEntity.model_validate_json(price.model_dump_json())
    except ValidationError as error:
        assert (
            error.errors()[0]["msg"]
            == "Value error, a dictionary association JSON input is an object with exactly one 'id' key."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("Exported reference was accepted as selection input")


def schema_modes() -> None:
    """Compare the transport schemas without claiming typed export properties."""
    validation = PriceCoreEntity.model_json_schema(mode="validation")["properties"]["currency"]["anyOf"][0]
    serialization = PriceCoreEntity.model_json_schema(mode="serialization")["properties"]["currency"]["anyOf"][0]
    assert validation["required"] == ["id"]
    assert validation["additionalProperties"] is False
    assert serialization["required"] == ["code", "display_name", "properties"]
    print("Input keys:", validation["required"])
    print("Output keys:", serialization["required"])


def main() -> None:
    """Run Python selection, JSON transport and schema modes."""
    python_selection()
    json_selection()
    schema_modes()


if __name__ == "__main__":
    main()
