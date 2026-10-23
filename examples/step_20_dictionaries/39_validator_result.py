"""A dictionary checks the completed value after user validation.
Run: .venv/bin/python examples/step_20_dictionaries/39_validator_result.py
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
            def replace(cls, labels: tuple[str, ...]) -> list[str]:
                """Return a value that violates the annotation."""
                return list(labels)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds list" in str(error)
    else:
        raise AssertionError("A mutable dictionary property was published")


if __name__ == "__main__":
    main()
