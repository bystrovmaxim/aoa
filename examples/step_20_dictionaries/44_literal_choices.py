"""Literal choices match both type and value.
Run: .venv/bin/python examples/step_20_dictionaries/44_literal_choices.py
"""

from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_unlisted_choice() -> None:
    """Refuse an after-validator result outside the literal choices."""
    try:

        class LiteralEnumEntity(BaseEnumEntity):
            """Declare one permitted choice."""

            choice: Literal["a"]
            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str) -> str:
                """Return a scalar outside the permitted choices."""
                return "b"
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "Literal['a']" in str(error)
    else:
        raise AssertionError("A literal result outside the choices was published")


def accept_listed_choice() -> None:
    """Accept another declared literal choice."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: Literal["a", "b"]
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: Literal["a", "b"]) -> str:
            """Return the completed value under examination."""
            return "b"

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == "b"
    assert type(ChoiceEnumEntity.ITEM.choice) is str


def reject_boolean_as_integer() -> None:
    """Distinguish a boolean from an integer literal."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: Literal[1]
            ITEM = value(code="item", display_name="Item", choice=1)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: Literal[1]) -> bool:
                """Return the completed value under examination."""
                return True
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected Literal[1]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def reject_integer_as_boolean() -> None:
    """Distinguish an integer from a boolean literal."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: Literal[True]
            ITEM = value(code="item", display_name="Item", choice=True)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: Literal[True]) -> int:
                """Return the completed value under examination."""
                return 1
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds int (expected Literal[True]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_unlisted_choice()
    accept_listed_choice()
    reject_boolean_as_integer()
    reject_integer_as_boolean()


if __name__ == "__main__":
    main()
