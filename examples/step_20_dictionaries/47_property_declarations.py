"""Property declarations distinguish nullability and integer types.
Run: .venv/bin/python examples/step_20_dictionaries/47_property_declarations.py
"""

from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_null_only_property() -> None:
    """Refuse a property annotated only None."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: None
            ITEM = value(code="item", display_name="Item", choice=None)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: field 'choice' is NoneType, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def accept_nullable_literal() -> None:
    """Allow absence alongside a declared literal choice."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: Literal["a", None]
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: Literal["a", None]) -> None:
            """Return the completed value under examination."""
            return None

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice is None
    assert type(ChoiceEnumEntity.ITEM.choice) is type(None)


def reject_boolean_integer() -> None:
    """Keep boolean results out of integer properties."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: int
            ITEM = value(code="item", display_name="Item", choice=1)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: int) -> bool:
                """Return the completed value under examination."""
                return True
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_null_only_property()
    accept_nullable_literal()
    reject_boolean_integer()


if __name__ == "__main__":
    main()
