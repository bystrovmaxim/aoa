"""Describe accepted reference input.

An input schema allows the code alone because the model already knows its description.
Run: uv run python examples/step_20_dictionaries/13_input_schema.py
"""

from jsonschema import Draft202012Validator
from pydantic import BaseModel

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe the supported currency."""
    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")

class Price(BaseModel):
    """Hold a dictionary reference."""
    currency: CurrencyEnumEntity


def main() -> None:
    """Run this one learning experiment."""
    schema = Price.model_json_schema(mode="validation")
    payload = {"currency": {"code": "eur"}}
    Draft202012Validator(schema).validate(payload)
    price = Price.model_validate(payload)
    print("Required input:", schema["properties"]["currency"]["required"])
    print("Resolved:", price.currency is CurrencyEnumEntity.EUR)
    assert price.currency is CurrencyEnumEntity.EUR


if __name__ == "__main__":
    main()
