# Validate dictionary values and export references

Dictionary members are shared values. Their property annotations restrict the types that can be declared. The completed member is now checked after user validation as well: a validator cannot turn a tuple property into a list and publish it as a dictionary member. Previously that result could pass the annotation check.

Keep custom validators consistent with the declared property type. A mismatched completed value raises `ValueError` while the dictionary class is created. The diagnostic identifies the member and property. The first example reproduces the refusal through the public declaration API.

## A dictionary checks the completed value after user validation.

[Script](../../examples/step_20_dictionaries/39_validator_result.py) · [Notebook](../../examples/step_20_dictionaries/39_validator_result.ipynb)

```python
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
```

Actual output:

```text
ValueError: LabelsEnumEntity: the property 'labels' of member 'ITEM' holds list (expected tuple[str, ...]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

## An exported dictionary reference validates against its serialization schema.

[Script](../../examples/step_20_dictionaries/40_export_schema.py) · [Notebook](../../examples/step_20_dictionaries/40_export_schema.ipynb)

```python
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
```

Actual output:

```text
{"rated": {"code": "item", "display_name": "Item", "properties": {"grade": "a", "note": null}}}
Export matches serialization schema
```

## A dictionary refuses a mutable item nested inside a tuple.

[Script](../../examples/step_20_dictionaries/42_validator_nested_list.py) · [Notebook](../../examples/step_20_dictionaries/42_validator_nested_list.ipynb)

```python
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
```

Actual output:

```text
ValueError: LabelsEnumEntity: the property 'labels[1]' of member 'ITEM' holds list (expected str); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

## A dictionary refuses an enum whose underlying value is mutable.

[Script](../../examples/step_20_dictionaries/43_mutable_enum_value.py) · [Notebook](../../examples/step_20_dictionaries/43_mutable_enum_value.ipynb)

```python
"""A dictionary refuses an enum whose underlying value is mutable.
Run: .venv/bin/python examples/step_20_dictionaries/43_mutable_enum_value.py
"""
from enum import Enum
from aoa.action_machine.domain import BaseEnumEntity, value

class Flags(Enum):
    """Name a flag carrying a mutable list."""
    X = ["a"]

def main() -> None:
    """Refuse the mutable enum property before publication."""
    try:
        class FlagsEnumEntity(BaseEnumEntity):
            """Declare the flag property."""
            flags: Flags
            ITEM = value(code="item", display_name="Item", flags=Flags.X)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "whose value is list" in str(error)
    else:
        raise AssertionError("A mutable enum value was published")

if __name__ == "__main__":
    main()
```

Actual output:

```text
ValueError: FlagsEnumEntity: the property 'flags' of member 'ITEM' holds Flags, whose value is list; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

## A dictionary refuses a validator returning the wrong immutable type.

[Script](../../examples/step_20_dictionaries/41_validator_wrong_type.py) · [Notebook](../../examples/step_20_dictionaries/41_validator_wrong_type.ipynb)

```python
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
```

Actual output:

```text
ValueError: LabelsEnumEntity: the property 'labels' of member 'ITEM' holds str (expected tuple[str, ...]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

## Export and migration

The serialization schema now retains the definitions used by enum properties. Previously this combination could fail during schema generation. Generate input schemas with `mode="validation"` and output schemas with `mode="serialization"`; validate the actual exported payload against the latter. No reference payload migration is required.

Every property emitted by serialization is required in the nested output object, including properties whose value is null. An excluded property is absent. Input can still contain only the dictionary code. Input schema validation checks the reference shape; resolving a code to a declared member remains runtime validation's responsibility.

## Confirmed boundaries

Two after-validator results still escape checking: a scalar outside its `Literal` choices, and `None` for a union that does not include `None`. These are implementation defects. A custom validator must preserve both constraints. The dictionary rule does not restrict lifecycle-status property types.

See [dictionary tutorial](../tutorials/step-20-dictionaries.md) and [explicit entity fields](explicit-entity-fields.md).
