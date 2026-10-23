"""Refuse Detail.

The property annotation is checked when the dictionary class is created.
Run: uv run python examples/step_20_dictionaries/36_nested_model.py
"""

from pydantic import BaseModel

from aoa.action_machine.domain import BaseEnumEntity, value


class Detail(BaseModel):
    """Describe a nested model that is outside the property contract."""
    count: int = 1


def main() -> None:
    """Run this one learning experiment."""
    try:
        class InvalidEnumEntity(BaseEnumEntity):
            """Attempt to declare an unsupported property type."""
            detail: Detail
            ITEM = value(code="item", display_name="Item")
    except ValueError as error:
        print(str(error))
        assert "field 'detail' is Detail" in str(error)
    else:
        raise AssertionError("The unsupported property was accepted")


if __name__ == "__main__":
    main()
