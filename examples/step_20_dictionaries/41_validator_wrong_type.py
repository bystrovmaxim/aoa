"""A dictionary refuses a validator returning the wrong immutable type.
Run: .venv/bin/python examples/step_20_dictionaries/41_validator_wrong_type.py
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
            def replace(cls, labels: tuple[str, ...]) -> str:
                """Return a value that violates the annotation."""
                return ",".join(labels)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds str" in str(error)
    else:
        raise AssertionError("A mutable dictionary property was published")


if __name__ == "__main__":
    main()
