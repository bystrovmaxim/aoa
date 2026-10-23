"""Apply a field serializer.

The dictionary controls how its date is presented to a consumer.
Run: uv run python examples/step_20_dictionaries/12_field_serializer.py
"""

import json
from datetime import date

from pydantic import field_serializer

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Give the edition date an explicit display format."""
    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))

    @field_serializer("published")
    def serialize_published(self, published: date) -> str:
        """Write the day before the month."""
        return published.strftime("%d/%m/%Y")


def main() -> None:
    """Run this one learning experiment."""
    reference = EditionEnumEntity.FIRST.to_reference()
    print(json.dumps(reference))
    assert reference["properties"]["published"] == "02/01/2020"


if __name__ == "__main__":
    main()
