"""Use a field named value.

Import the declaration factory under another name when the class binds value itself.
Run: uv run python examples/step_20_dictionaries/17_factory_alias.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.domain import value as declared


class SizeEnumEntity(BaseEnumEntity):
    """Describe a size using a field named value."""
    value: int = Field(description="Size in millimetres")
    SMALL = declared(code="small", display_name="Small", value=10)


def main() -> None:
    """Run this one learning experiment."""
    print("Size:", SizeEnumEntity.SMALL.value)
    print("Codes:", SizeEnumEntity.codes())
    assert SizeEnumEntity.SMALL.value == 10


if __name__ == "__main__":
    main()
