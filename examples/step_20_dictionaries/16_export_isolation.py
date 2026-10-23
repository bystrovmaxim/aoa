"""Keep exported arrays separate.

A consumer edits an exported JSON array without changing the shared catalogue member.
Run: uv run python examples/step_20_dictionaries/16_export_isolation.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Keep immutable aliases on the shared currency."""
    aliases: tuple[str, ...]
    EUR = value(code="eur", display_name="Euro", aliases=("EUR", "€"))


def main() -> None:
    """Run this one learning experiment."""
    reference = CurrencyEnumEntity.EUR.to_reference()
    reference["properties"]["aliases"].append("edited")
    print("Payload:", reference["properties"]["aliases"])
    print("Declared:", CurrencyEnumEntity.EUR.aliases)
    print("Fresh export:", CurrencyEnumEntity.EUR.to_reference()["properties"]["aliases"])
    assert CurrencyEnumEntity.EUR.aliases == ("EUR", "€")


if __name__ == "__main__":
    main()
