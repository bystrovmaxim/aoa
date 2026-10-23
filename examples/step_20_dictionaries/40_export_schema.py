"""An exported dictionary reference validates against its serialization schema.
Run: .venv/bin/python examples/step_20_dictionaries/40_export_schema.py
"""

import json
from enum import Enum
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field
from aoa.action_machine.domain import BaseEnumEntity, value


class Grade(Enum):
    """Name the accepted grades."""
    A = "a"
    B = "b"


class RatedEnumEntity(BaseEnumEntity):
    """Declare an enum property and an optional note."""
    grade: Grade
    note: str | None = None
    hidden: str = Field(default="private", exclude=True)
    ITEM = value(code="item", display_name="Item", grade=Grade.A)


class Holder(BaseModel):
    """Accept a dictionary reference."""
    rated: RatedEnumEntity


def main() -> None:
    """Validate the input and real export against their respective schemas."""
    incoming = {"rated": {"code": "item"}}
    Draft202012Validator(Holder.model_json_schema(mode="validation")).validate(incoming)
    exported = Holder.model_validate(incoming).model_dump(mode="json")
    schema = Holder.model_json_schema(mode="serialization")
    Draft202012Validator(schema).validate(exported)
    print(json.dumps(exported, sort_keys=True))
    print("Export matches serialization schema")
    properties = schema["properties"]["rated"]["properties"]["properties"]
    assert set(properties["required"]) == {"grade", "note"}
    assert "hidden" not in properties["properties"]
    assert exported["rated"]["properties"] == {"grade": "a", "note": None}
    assert schema["$defs"]


if __name__ == "__main__":
    main()
