"""Refuse list[str].

The property annotation is checked when the dictionary class is created.
Run: uv run python examples/step_20_dictionaries/30_mutable_list.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


def main() -> None:
    """Run this one learning experiment."""
    try:
        class InvalidEnumEntity(BaseEnumEntity):
            """Attempt to declare an unsupported property type."""
            detail: list[str]
            ITEM = value(code="item", display_name="Item")
    except ValueError as error:
        print(str(error))
        assert "field 'detail' is list" in str(error)
    else:
        raise AssertionError("The unsupported property was accepted")


if __name__ == "__main__":
    main()
