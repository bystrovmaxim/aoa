"""Describe the emitted reference.

The output schema names the property that a consumer will receive.
Run: uv run python examples/step_20_dictionaries/14_output_schema.py
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
    schema = Price.model_json_schema(mode="serialization")
    reference_schema = schema["properties"]["currency"]
    price = Price(currency=CurrencyEnumEntity.EUR)
    Draft202012Validator(schema).validate(price.model_dump(mode="json"))
    properties = reference_schema["properties"]["properties"]
    print("Required output:", reference_schema["required"])
    print("Property definitions:", properties["properties"])
    print("Extra keys:", properties["additionalProperties"])
    assert properties["properties"]["symbol"] == {"type": "string"}


if __name__ == "__main__":
    main()
