"""Keep a collection as a tuple.

A dictionary can describe several aliases without carrying a mutable list.
Run: uv run python examples/step_20_dictionaries/10_tuple_property.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Give a currency a fixed collection of aliases."""
    aliases: tuple[str, ...]
    EUR = value(code="eur", display_name="Euro", aliases=("EUR", "€"))


def main() -> None:
    """Run this one learning experiment."""
    print("Aliases:", CurrencyEnumEntity.EUR.aliases)
    print("Python type:", type(CurrencyEnumEntity.EUR.aliases).__name__)
    assert CurrencyEnumEntity.EUR.aliases == ("EUR", "€")


if __name__ == "__main__":
    main()
