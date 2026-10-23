"""Property declarations distinguish nullability and exact leaf types.
Run: .venv/bin/python examples/step_20_dictionaries/47_property_declarations.py
"""

from datetime import date, datetime
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


def reject_subclass_results() -> None:
    """Refuse a subclass result for a float and for a date property."""
    try:

        class RatioEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            ratio: float
            ITEM = value(code="item", display_name="Item", ratio=1.5)

            @field_validator("ratio", mode="after")
            @classmethod
            def replace(cls, ratio: float) -> int:
                """Return the completed value under examination."""
                return 1
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds int (expected float)" in str(error)
    else:
        raise AssertionError("An integer result was published for a float property")

    try:

        class DayEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            day: date
            ITEM = value(code="item", display_name="Item", day=date(2020, 1, 2))

            @field_validator("day", mode="after")
            @classmethod
            def replace(cls, day: date) -> datetime:
                """Return the completed value under examination."""
                return datetime(2020, 1, 2, 3, 4)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds datetime (expected date)" in str(error)
    else:
        raise AssertionError("A datetime result was published for a date property")


def accept_declared_leaf_types() -> None:
    """Accept the declared type, and the coercion Pydantic applies before the check."""

    class RatioEnumEntity(BaseEnumEntity):
        """Declare the property under examination with an integer input."""

        ratio: float
        ITEM = value(code="item", display_name="Item", ratio=1)

    print("Completed value:", repr(RatioEnumEntity.ITEM.ratio))
    assert RatioEnumEntity.ITEM.ratio == 1.0
    assert type(RatioEnumEntity.ITEM.ratio) is float


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_null_only_property()
    accept_nullable_literal()
    reject_boolean_integer()
    reject_subclass_results()
    accept_declared_leaf_types()


if __name__ == "__main__":
    main()
