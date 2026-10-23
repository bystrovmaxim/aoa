"""Describe the serialized property type.

A serializer that returns text makes its output property a string.
Run: uv run python examples/step_20_dictionaries/15_serializer_schema.py
"""

from datetime import date

from pydantic import field_serializer

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Format an edition date as text."""
    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))

    @field_serializer("published")
    def serialize_published(self, published: date) -> str:
        """Return a day-first date string."""
        return published.strftime("%d/%m/%Y")


def main() -> None:
    """Run this one learning experiment."""
    schema = EditionEnumEntity.model_json_schema(mode="serialization")
    property_schema = schema["properties"]["properties"]["properties"]["published"]
    print("Emitted type:", property_schema)
    assert property_schema == {"type": "string"}


if __name__ == "__main__":
    main()
