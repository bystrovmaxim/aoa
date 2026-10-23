"""Declare a value explicitly.

The class describes the fields; value() supplies the fields of one catalogue member.
Run: uv run python examples/step_20_dictionaries/00_declaration.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe one supported currency."""
    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


def main() -> None:
    """Run this one learning experiment."""
    print("Instance:", isinstance(CurrencyEnumEntity.EUR, CurrencyEnumEntity))
    print("Codes:", CurrencyEnumEntity.codes())
    print("Shared:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
    print("Symbol:", CurrencyEnumEntity.EUR.symbol)
    assert CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR


if __name__ == "__main__":
    main()
