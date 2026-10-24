# Validate dictionary values and export references

Dictionary members are shared values. Their property annotations restrict the types that can be declared. The completed member is now checked after user validation as well: a validator cannot turn a tuple property into a list, return a value outside the property's `Literal` choices, or return null when the union does not include it, and publish any of those as a dictionary member. Previously those results could pass the annotation check.

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

## Migrate completed values

Previously, an after-validator could publish a value outside its literal choices or null for a union that excluded it. Those class declarations now raise `ValueError` before the member is published. Integer properties also refuse booleans, even though Python treats `bool` as a subclass of `int`. A leaf property compares the exact declared type, so an `int` result is refused for a `float` property and a `datetime` result is refused for a `date` property. Input is still coerced before the check: a `float` property declared with `1` holds `1.0`. Fix the validator to return the declared type and choice; change an annotation only if the additional value belongs to the intended vocabulary.

| Property annotation | Completed value | Result |
| --- | --- | --- |
| `Literal["a"]` | `"b"` | Refused |
| `Literal["a", "b"]` | `"b"` | Accepted |
| `Literal[1]` | `True` | Refused |
| `Literal[True]` | `1` | Refused |
| `str | int` | `None` | Refused |
| `str | int | None` | `None` | Accepted |
| `Literal["a", None]` | `None` | Accepted |
| `int` | `True` | Refused |
| `float` | `1` (an `int`) | Refused; return `1.0` |
| `date` | `datetime(...)` | Refused; return a `date` |
| `None` alone | Any declaration | Refused at annotation checking |

A nullable annotation permits null; it does not by itself make a containing model field omittable. Tuple checks apply the item annotation and name the failing index in the diagnostic. The cases below show both refusals and accepted neighbors.

## Literal choices match both type and value

Use a literal when the property has a fixed set of choices. The validator may choose another listed value, but equality alone does not make a value legal: boolean and integer choices keep their own types.

[Script](../../examples/step_20_dictionaries/44_literal_choices.py) · [Notebook](../../examples/step_20_dictionaries/44_literal_choices.ipynb)

Run the complete script in a fresh process, or run the notebook cases in order.

```python
"""Literal choices match both type and value.
Run: .venv/bin/python examples/step_20_dictionaries/44_literal_choices.py
"""

from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_unlisted_choice() -> None:
    """Refuse an after-validator result outside the literal choices."""
    try:

        class LiteralEnumEntity(BaseEnumEntity):
            """Declare one permitted choice."""

            choice: Literal["a"]
            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str) -> str:
                """Return a scalar outside the permitted choices."""
                return "b"
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "Literal['a']" in str(error)
    else:
        raise AssertionError("A literal result outside the choices was published")


def accept_listed_choice() -> None:
    """Accept another declared literal choice."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: Literal["a", "b"]
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: Literal["a", "b"]) -> str:
            """Return the completed value under examination."""
            return "b"

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == "b"
    assert type(ChoiceEnumEntity.ITEM.choice) is str


def reject_boolean_as_integer() -> None:
    """Distinguish a boolean from an integer literal."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: Literal[1]
            ITEM = value(code="item", display_name="Item", choice=1)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: Literal[1]) -> bool:
                """Return the completed value under examination."""
                return True
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected Literal[1]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def reject_integer_as_boolean() -> None:
    """Distinguish an integer from a boolean literal."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: Literal[True]
            ITEM = value(code="item", display_name="Item", choice=True)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: Literal[True]) -> int:
                """Return the completed value under examination."""
                return 1
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds int (expected Literal[True]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_unlisted_choice()
    accept_listed_choice()
    reject_boolean_as_integer()
    reject_integer_as_boolean()


if __name__ == "__main__":
    main()
```

Actual output:

```text
ValueError: LiteralEnumEntity: the property 'choice' of member 'ITEM' holds str (expected Literal['a']); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
Completed value: 'b'
ValueError: ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected Literal[1]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
ValueError: ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds int (expected Literal[True]); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

## Unions accept declared member types and explicitly permitted null

A union allows any of its declared member types. Returning a different member type is valid. Returning null is valid only when the union explicitly includes it.

[Script](../../examples/step_20_dictionaries/45_union_nullability.py) · [Notebook](../../examples/step_20_dictionaries/45_union_nullability.ipynb)

Run the complete script in a fresh process, or run the notebook cases in order.

```python
"""Unions accept declared member types and explicitly permitted null.
Run: .venv/bin/python examples/step_20_dictionaries/45_union_nullability.py
"""

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_unlisted_null() -> None:
    """Refuse null when the union excludes it."""
    try:

        class UnionEnumEntity(BaseEnumEntity):
            """Declare a union without null."""

            choice: str | int
            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str | int) -> None:
                """Return null although the annotation excludes it."""
                return None
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds NoneType" in str(error)
    else:
        raise AssertionError("Null was published for a non-null union")


def accept_member_type() -> None:
    """Accept another member type of the union."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: str | int
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int) -> int:
            """Return the completed value under examination."""
            return 10

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == 10
    assert type(ChoiceEnumEntity.ITEM.choice) is int


def accept_nullable_union() -> None:
    """Accept null when the union includes it."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: str | int | None
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int | None) -> None:
            """Return the completed value under examination."""
            return None

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice is None
    assert type(ChoiceEnumEntity.ITEM.choice) is type(None)


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_unlisted_null()
    accept_member_type()
    accept_nullable_union()


if __name__ == "__main__":
    main()
```

Actual output:

```text
ValueError: UnionEnumEntity: the property 'choice' of member 'ITEM' holds NoneType (expected str | int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
Completed value: 10
Completed value: None
```

## Tuple items follow their annotations and refusals name the item index

A tuple applies the property rule to each item. These cases compare invalid literal and null items with a permitted nullable item, so the error path shows exactly where the rejected value occurred.

[Script](../../examples/step_20_dictionaries/46_tuple_item_validation.py) · [Notebook](../../examples/step_20_dictionaries/46_tuple_item_validation.ipynb)

Run the complete script in a fresh process, or run the notebook cases in order.

```python
"""Tuple items follow their annotations and refusals name the item index.
Run: .venv/bin/python examples/step_20_dictionaries/46_tuple_item_validation.py
"""

from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_tuple_literal() -> None:
    """Identify a tuple item outside its literal choices."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: tuple[Literal["a"], ...]
            ITEM = value(code="item", display_name="Item", choice=("a",))

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: tuple[Literal["a"], ...]) -> tuple[str, ...]:
                """Return the completed value under examination."""
                return ("a", "b")
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds str (expected Literal['a']); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def reject_tuple_null() -> None:
    """Identify null in a non-nullable tuple item."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: tuple[str | int, ...]
            ITEM = value(code="item", display_name="Item", choice=("a",))

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: tuple[str | int, ...]) -> tuple[str | int | None, ...]:
                """Return the completed value under examination."""
                return ("a", None)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds NoneType (expected str | int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def accept_nullable_item() -> None:
    """Accept null in a nullable tuple item."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: tuple[str | None, ...]
        ITEM = value(code="item", display_name="Item", choice=("a",))

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: tuple[str | None, ...]) -> tuple[str | None, ...]:
            """Return the completed value under examination."""
            return ("a", None)

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice == ("a", None)
    assert type(ChoiceEnumEntity.ITEM.choice) is type(("a", None))


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_tuple_literal()
    reject_tuple_null()
    accept_nullable_item()


if __name__ == "__main__":
    main()
```

Actual output:

```text
ValueError: ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds str (expected Literal['a']); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
ValueError: ChoiceEnumEntity: the property 'choice[1]' of member 'ITEM' holds NoneType (expected str | int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
Completed value: ('a', None)
```

## Property declarations distinguish nullability and exact leaf types

Choose an annotation that describes a useful property. A property consisting only of null is refused; a literal can include null alongside another choice. Integer properties keep integers rather than accepting boolean results, and a leaf keeps its exact type: an `int` is not a `float`, and a `datetime` is not a `date`.

[Script](../../examples/step_20_dictionaries/47_property_declarations.py) · [Notebook](../../examples/step_20_dictionaries/47_property_declarations.ipynb)

Run the complete script in a fresh process, or run the notebook cases in order.

```python
"""Property declarations distinguish nullability and exact leaf types.
Run: .venv/bin/python examples/step_20_dictionaries/47_property_declarations.py
"""

from datetime import date, datetime
from typing import Literal

from pydantic import field_validator

from aoa.action_machine.domain import BaseEnumEntity, value


def reject_null_only_property() -> None:
    """Refuse a property annotated only None."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: None
            ITEM = value(code="item", display_name="Item", choice=None)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: field 'choice' is NoneType, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def accept_nullable_literal() -> None:
    """Allow absence alongside a declared literal choice."""

    class ChoiceEnumEntity(BaseEnumEntity):
        """Declare the property under examination."""

        choice: Literal["a", None]
        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: Literal["a", None]) -> None:
            """Return the completed value under examination."""
            return None

    print("Completed value:", repr(ChoiceEnumEntity.ITEM.choice))
    assert ChoiceEnumEntity.ITEM.choice is None
    assert type(ChoiceEnumEntity.ITEM.choice) is type(None)


def reject_boolean_integer() -> None:
    """Keep boolean results out of integer properties."""
    try:

        class ChoiceEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            choice: int
            ITEM = value(code="item", display_name="Item", choice=1)

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: int) -> bool:
                """Return the completed value under examination."""
                return True
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert (
            str(error)
            == "ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types."
        )
    else:
        raise AssertionError("The invalid dictionary declaration was accepted")


def reject_subclass_results() -> None:
    """Refuse a subclass result for a float and for a date property."""
    try:

        class RatioEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            ratio: float
            ITEM = value(code="item", display_name="Item", ratio=1.5)

            @field_validator("ratio", mode="after")
            @classmethod
            def replace(cls, ratio: float) -> int:
                """Return the completed value under examination."""
                return 1
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds int (expected float)" in str(error)
    else:
        raise AssertionError("An integer result was published for a float property")

    try:

        class DayEnumEntity(BaseEnumEntity):
            """Declare the property under examination."""

            day: date
            ITEM = value(code="item", display_name="Item", day=date(2020, 1, 2))

            @field_validator("day", mode="after")
            @classmethod
            def replace(cls, day: date) -> datetime:
                """Return the completed value under examination."""
                return datetime(2020, 1, 2, 3, 4)
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
        assert "holds datetime (expected date)" in str(error)
    else:
        raise AssertionError("A datetime result was published for a date property")


def accept_declared_leaf_types() -> None:
    """Accept the declared type, and the coercion Pydantic applies before the check."""

    class RatioEnumEntity(BaseEnumEntity):
        """Declare the property under examination with an integer input."""

        ratio: float
        ITEM = value(code="item", display_name="Item", ratio=1)

    print("Completed value:", repr(RatioEnumEntity.ITEM.ratio))
    assert RatioEnumEntity.ITEM.ratio == 1.0
    assert type(RatioEnumEntity.ITEM.ratio) is float


def main() -> None:
    """Run the refusals and accepted neighbors in this scenario."""
    reject_null_only_property()
    accept_nullable_literal()
    reject_boolean_integer()
    reject_subclass_results()
    accept_declared_leaf_types()


if __name__ == "__main__":
    main()
```

Actual output:

```text
ValueError: ChoiceEnumEntity: field 'choice' is NoneType, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
Completed value: None
ValueError: ChoiceEnumEntity: the property 'choice' of member 'ITEM' holds bool (expected int); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
ValueError: RatioEnumEntity: the property 'ratio' of member 'ITEM' holds int (expected float); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
ValueError: DayEnumEntity: the property 'day' of member 'ITEM' holds datetime (expected date); supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
Completed value: 1.0
```

## Export and migration

The serialization schema now retains the definitions used by enum properties. Previously this combination could fail during schema generation. Generate input schemas with `mode="validation"` and output schemas with `mode="serialization"`; validate the actual exported payload against the latter. No reference payload migration is required.

Every property emitted by serialization is required in the nested output object, including properties whose value is null. An excluded property is absent. Standalone dictionary/ordinary Pydantic DTO input can still contain only the dictionary code. Entity relationship JSON input instead uses an id object; see [dictionary selections](dictionary-references.md). Input schema validation checks the reference shape; resolving a code to a declared member remains runtime validation's responsibility.

## Checked boundaries

Literal choices match by both type and value. A union accepts null only if one of its members is `None`; a literal may also list `None` explicitly. An annotation consisting only of `None` is not a supported dictionary property. A leaf compares the exact type, so a subclass is refused: `True` is not an `int`, `1` is not a `float`, and a `datetime` is not a `date`. These checks run while the dictionary class is created and also reach tuple items. The dictionary rule does not restrict lifecycle-status property types.

Input and output schemas retain their existing responsibilities. The completed-value fix does not change the reference payload. See the [dictionary tutorial](../tutorials/step-20-dictionaries.md), [invariant reference](../reference/intents-and-invariants.md), and [explicit entity fields](explicit-entity-fields.md).

## Dictionary reference declarations

An entity field selecting a catalogue uses `Annotated[AssociationOne[D], NoInverse()] = Field(description="...")`. Bare dictionary fields are refused at model build. The plain `Holder(BaseModel)` used in the export examples above is a DTO, not an `@entity` host, so its direct dictionary validation remains supported. Do not copy that DTO field declaration onto an entity.

For entity selections, Python input is an explicit wrapper and JSON input is an id-only object. Export still uses the canonical dictionary reference, but the association's serialization schema currently lacks typed custom-property definitions. The standalone export schema demonstrated above retains them. See [supported forms, migration and exact refusals](dictionary-references.md), the [transport script](../../examples/step_20_dictionaries/56_selection_transport.py), its [executed notebook](../../examples/step_20_dictionaries/56_selection_transport.ipynb), and the [schema limitation](../reports/complete-relationship-verification.md#association-serialization-schema).
