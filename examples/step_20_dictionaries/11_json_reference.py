"""Export a JSON reference.

A native date becomes a string at the reference boundary.
Run: uv run python examples/step_20_dictionaries/11_json_reference.py
"""

import json
from datetime import date

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Describe a fixed catalogue edition."""
    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))


def main() -> None:
    """Run this one learning experiment."""
    item = EditionEnumEntity.FIRST
    print("Python dump type:", type(item.model_dump()["properties"]["published"]).__name__)
    reference = item.to_reference()
    print("Reference type:", type(reference["properties"]["published"]).__name__)
    print(json.dumps(reference))
    assert reference == item.model_dump(mode="json")


if __name__ == "__main__":
    main()
