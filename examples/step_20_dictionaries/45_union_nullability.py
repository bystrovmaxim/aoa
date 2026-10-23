"""Unions accept declared member types and explicitly permitted null.
Run: .venv/bin/python examples/step_20_dictionaries/45_union_nullability.py
"""

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_unlisted_null() -> None:
    """Refuse null when the union excludes it."""
    try:

        class UnionEnumEntity(BaseEnumEntity):
            """Declare a union without null."""

            choice: str | int
            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str | int) -> None:
                """Return null although the annotation excludes it."""
                return None
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds NoneType" in str(error)
    else:
        raise AssertionError("Null was published for a non-null union")


def accept_member_type() -> None:
    """Accept another member type of the union."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: str | int
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int) -> int:
            """Return the completed value under examination."""
            return 10

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == 10
    assert type(ChoiceEnumEntity.ITEM.choice) is int


def accept_nullable_union() -> None:
    """Accept null when the union includes it."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: str | int | None
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int | None) -> None:
            """Return the completed value under examination."""
            return None

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice is None
    assert type(ChoiceEnumEntity.ITEM.choice) is type(None)


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_unlisted_null()
    accept_member_type()
    accept_nullable_union()


if __name__ == "__main__":
    main()
