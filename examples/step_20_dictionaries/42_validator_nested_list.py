"""A dictionary refuses a mutable item nested inside a tuple.
Run: .venv/bin/python examples/step_20_dictionaries/42_validator_nested_list.py
"""

from pydantic import field_validator
from aoa.action_machine.domain import BaseEnumEntity, value


def main() -> None:
    """Refuse a validator that replaces a tuple with a list."""
    try:
        class LabelsEnumEntity(BaseEnumEntity):
            """Declare immutable labels."""
            labels: tuple[str, ...]
            ITEM = value(code="item", display_name="Item", labels=("a",))

            @field_validator("labels", mode="after")
            @classmethod
            def replace(cls, labels: tuple[str, ...]) -> tuple[object, ...]:
                """Return a value that violates the annotation."""
                return ("a", ["b"])
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "labels[1]" in str(error)
    else:
        raise AssertionError("A mutable dictionary property was published")


if __name__ == "__main__":
    main()
