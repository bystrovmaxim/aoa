"""Tuple items follow their annotations and refusals name the item index.
Run: .venv/bin/python examples/step_20_dictionaries/46_tuple_item_validation.py
"""

from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_tuple_literal() -> None:
    """Identify a tuple item outside its literal choices."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: tuple[Literal["a"], ...]
            ITEM = value(code="item", display_name="Item", choice=("a",))

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: tuple[Literal["a"], ...]) -> tuple[str, ...]:
                """Return the completed value under examination."""
                return ("a", "b")
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds str (expected Literal['a']); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def reject_tuple_null() -> None:
    """Identify null in a non-nullable tuple item."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: tuple[str | int, ...]
            ITEM = value(code="item", display_name="Item", choice=("a",))

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: tuple[str | int, ...]) -> tuple[str | int | None, ...]:
                """Return the completed value under examination."""
                return ("a", None)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds NoneType (expected str | int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def accept_nullable_item() -> None:
    """Accept null in a nullable tuple item."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: tuple[str | None, ...]
        ITEM = value(code="item", display_name="Item", choice=("a",))

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: tuple[str | None, ...]) -> tuple[str | None, ...]:
            """Return the completed value under examination."""
            return ("a", None)

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == ("a", None)
    assert type(ChoiceEnumEntity.ITEM.choice) is type(("a", None))


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_tuple_literal()
    reject_tuple_null()
    accept_nullable_item()


if __name__ == "__main__":
    main()
