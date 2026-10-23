"""A dictionary refuses an enum whose underlying value is mutable.
Run: .venv/bin/python examples/step_20_dictionaries/43_mutable_enum_value.py
"""
from enum import Enum
from aoa.action_machine.domain import BaseEnumEntity, value

class Flags(Enum):
    """Name a flag carrying a mutable list."""
    X = ["a"]

def main() -> None:
    """Refuse the mutable enum property before publication."""
    try:
        class FlagsEnumEntity(BaseEnumEntity):
            """Declare the flag property."""
            flags: Flags
            ITEM = value(code="item", display_name="Item", flags=Flags.X)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "whose value is list" in str(error)
    else:
        raise AssertionError("A mutable enum value was published")

if __name__ == "__main__":
    main()
