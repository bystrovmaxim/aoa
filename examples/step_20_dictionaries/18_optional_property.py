"""Allow an absent description.

An optional descriptive field can have no value while the dictionary member still exists.
Run: uv run python examples/step_20_dictionaries/18_optional_property.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Permit an omitted explanatory note."""
    note: str | None = None
    EUR = value(code="eur", display_name="Euro")


def main() -> None:
    """Run this one learning experiment."""
    print("Note:", CurrencyEnumEntity.EUR.note)
    print("Properties:", CurrencyEnumEntity.EUR.to_reference()["properties"])
    assert CurrencyEnumEntity.EUR.note is None


if __name__ == "__main__":
    main()
