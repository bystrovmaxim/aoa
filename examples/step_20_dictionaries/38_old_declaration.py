"""Recognize the removed declaration syntax.

The class name is no longer replaced by a hidden declaration function.
Run: uv run python examples/step_20_dictionaries/38_old_declaration.py
"""

from aoa.action_machine.domain import BaseEnumEntity


def main() -> None:
    """Run this one learning experiment."""
    try:
        class OldEnumEntity(BaseEnumEntity):
            """Attempt to use the class before it exists."""
            EUR = OldEnumEntity(code="eur", display_name="Euro")
    except NameError:
        print("Old declaration: NameError")
    else:
        raise AssertionError("The removed declaration alias was accepted")


if __name__ == "__main__":
    main()
