# Closed dictionaries: declare values and use references

A dictionary declares the allowed reference values in its class body. Use the imported `value(...)` factory for each member. A typed reference resolves a code to a declared member. Export includes the code, human label and serialized properties.

## Migrate an existing declaration

Keep the dictionary's declared values and reference payloads. Custom validators must return values consistent with their annotations: completed members are now checked after validation, rather than relying only on the annotation. A tuple property cannot be replaced by a list. The exact refusal appears below.

Serialization schemas now retain the definitions needed by enum properties. Regenerate output schemas with `mode="serialization"`. Every emitted nested property is required, including null-valued properties; excluded properties are absent. Validation schemas still accept a code-only reference.

## Declare the vocabulary

Run this complete example in a fresh Python process.

[Script](../../examples/step_20_dictionaries/00_declaration.py) · [Notebook](../../examples/step_20_dictionaries/00_declaration.ipynb)

```python
"""Declare a value explicitly.

The class describes the fields; value() supplies the fields of one catalogue member.
Run: uv run python examples/step_20_dictionaries/00_declaration.py
"""

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe one supported currency."""
    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


def main() -> None:
    """Run this one learning experiment."""
    print("Instance:", isinstance(CurrencyEnumEntity.EUR, CurrencyEnumEntity))
    print("Codes:", CurrencyEnumEntity.codes())
    print("Shared:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
    print("Symbol:", CurrencyEnumEntity.EUR.symbol)
    assert CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR


if __name__ == "__main__":
    main()
```

Actual output:

```text
Instance: True
Codes: ['eur']
Shared: True
Symbol: €
```

## Preserve property types after validation

Run this complete example in a fresh Python process.

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

## Validate the real exported reference

Run this complete example in a fresh Python process.

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

## Read a refusal as a specific contract violation

The following cases are separate scripts and notebooks. Each was executed against the current tree; caught refusals print their type and actual message. Use a fresh process for each case.

| Case | Runnable script | Executed notebook |
| --- | --- | --- |
| reference field | [01_reference_field](../../examples/step_20_dictionaries/01_reference_field.py) | [Notebook](../../examples/step_20_dictionaries/01_reference_field.ipynb) |
| reference payload | [02_reference_payload](../../examples/step_20_dictionaries/02_reference_payload.py) | [Notebook](../../examples/step_20_dictionaries/02_reference_payload.ipynb) |
| serialization | [03_serialization](../../examples/step_20_dictionaries/03_serialization.py) | [Notebook](../../examples/step_20_dictionaries/03_serialization.ipynb) |
| storage mapping | [04_storage_mapping](../../examples/step_20_dictionaries/04_storage_mapping.py) | [Notebook](../../examples/step_20_dictionaries/04_storage_mapping.ipynb) |
| optional | [05_optional](../../examples/step_20_dictionaries/05_optional.py) | [Notebook](../../examples/step_20_dictionaries/05_optional.ipynb) |
| inheritance | [06_inheritance](../../examples/step_20_dictionaries/06_inheritance.py) | [Notebook](../../examples/step_20_dictionaries/06_inheritance.ipynb) |
| frozen | [07_frozen](../../examples/step_20_dictionaries/07_frozen.py) | [Notebook](../../examples/step_20_dictionaries/07_frozen.ipynb) |
| graph | [08_graph](../../examples/step_20_dictionaries/08_graph.py) | [Notebook](../../examples/step_20_dictionaries/08_graph.ipynb) |
| erd | [09_erd](../../examples/step_20_dictionaries/09_erd.py) | [Notebook](../../examples/step_20_dictionaries/09_erd.ipynb) |
| tuple property | [10_tuple_property](../../examples/step_20_dictionaries/10_tuple_property.py) | [Notebook](../../examples/step_20_dictionaries/10_tuple_property.ipynb) |
| json reference | [11_json_reference](../../examples/step_20_dictionaries/11_json_reference.py) | [Notebook](../../examples/step_20_dictionaries/11_json_reference.ipynb) |
| field serializer | [12_field_serializer](../../examples/step_20_dictionaries/12_field_serializer.py) | [Notebook](../../examples/step_20_dictionaries/12_field_serializer.ipynb) |
| input schema | [13_input_schema](../../examples/step_20_dictionaries/13_input_schema.py) | [Notebook](../../examples/step_20_dictionaries/13_input_schema.ipynb) |
| output schema | [14_output_schema](../../examples/step_20_dictionaries/14_output_schema.py) | [Notebook](../../examples/step_20_dictionaries/14_output_schema.ipynb) |
| serializer schema | [15_serializer_schema](../../examples/step_20_dictionaries/15_serializer_schema.py) | [Notebook](../../examples/step_20_dictionaries/15_serializer_schema.ipynb) |
| export isolation | [16_export_isolation](../../examples/step_20_dictionaries/16_export_isolation.py) | [Notebook](../../examples/step_20_dictionaries/16_export_isolation.ipynb) |
| factory alias | [17_factory_alias](../../examples/step_20_dictionaries/17_factory_alias.py) | [Notebook](../../examples/step_20_dictionaries/17_factory_alias.ipynb) |
| optional property | [18_optional_property](../../examples/step_20_dictionaries/18_optional_property.py) | [Notebook](../../examples/step_20_dictionaries/18_optional_property.ipynb) |
| bare code | [20_bare_code](../../examples/step_20_dictionaries/20_bare_code.py) | [Notebook](../../examples/step_20_dictionaries/20_bare_code.ipynb) |
| unknown code | [21_unknown_code](../../examples/step_20_dictionaries/21_unknown_code.py) | [Notebook](../../examples/step_20_dictionaries/21_unknown_code.ipynb) |
| copy | [22_copy](../../examples/step_20_dictionaries/22_copy.py) | [Notebook](../../examples/step_20_dictionaries/22_copy.ipynb) |
| missing code | [23_missing_code](../../examples/step_20_dictionaries/23_missing_code.py) | [Notebook](../../examples/step_20_dictionaries/23_missing_code.ipynb) |
| blank reference | [24_blank_reference](../../examples/step_20_dictionaries/24_blank_reference.py) | [Notebook](../../examples/step_20_dictionaries/24_blank_reference.ipynb) |
| flat fields | [25_flat_fields](../../examples/step_20_dictionaries/25_flat_fields.py) | [Notebook](../../examples/step_20_dictionaries/25_flat_fields.ipynb) |
| duplicate code | [26_duplicate_code](../../examples/step_20_dictionaries/26_duplicate_code.py) | [Notebook](../../examples/step_20_dictionaries/26_duplicate_code.ipynb) |
| blank code | [27_blank_code](../../examples/step_20_dictionaries/27_blank_code.py) | [Notebook](../../examples/step_20_dictionaries/27_blank_code.ipynb) |
| blank label | [28_blank_label](../../examples/step_20_dictionaries/28_blank_label.py) | [Notebook](../../examples/step_20_dictionaries/28_blank_label.ipynb) |
| empty dictionary | [29_empty_dictionary](../../examples/step_20_dictionaries/29_empty_dictionary.py) | [Notebook](../../examples/step_20_dictionaries/29_empty_dictionary.ipynb) |
| mutable list | [30_mutable_list](../../examples/step_20_dictionaries/30_mutable_list.py) | [Notebook](../../examples/step_20_dictionaries/30_mutable_list.ipynb) |
| mutable dict | [31_mutable_dict](../../examples/step_20_dictionaries/31_mutable_dict.py) | [Notebook](../../examples/step_20_dictionaries/31_mutable_dict.ipynb) |
| mutable set | [32_mutable_set](../../examples/step_20_dictionaries/32_mutable_set.py) | [Notebook](../../examples/step_20_dictionaries/32_mutable_set.ipynb) |
| frozenset | [33_frozenset](../../examples/step_20_dictionaries/33_frozenset.py) | [Notebook](../../examples/step_20_dictionaries/33_frozenset.ipynb) |
| nested mutable | [34_nested_mutable](../../examples/step_20_dictionaries/34_nested_mutable.py) | [Notebook](../../examples/step_20_dictionaries/34_nested_mutable.ipynb) |
| any property | [35_any_property](../../examples/step_20_dictionaries/35_any_property.py) | [Notebook](../../examples/step_20_dictionaries/35_any_property.ipynb) |
| nested model | [36_nested_model](../../examples/step_20_dictionaries/36_nested_model.py) | [Notebook](../../examples/step_20_dictionaries/36_nested_model.ipynb) |
| optional mutable | [37_optional_mutable](../../examples/step_20_dictionaries/37_optional_mutable.py) | [Notebook](../../examples/step_20_dictionaries/37_optional_mutable.ipynb) |
| old declaration | [38_old_declaration](../../examples/step_20_dictionaries/38_old_declaration.py) | [Notebook](../../examples/step_20_dictionaries/38_old_declaration.ipynb) |
| validator nested list | [42_validator_nested_list](../../examples/step_20_dictionaries/42_validator_nested_list.py) | [Notebook](../../examples/step_20_dictionaries/42_validator_nested_list.ipynb) |
| mutable enum value | [43_mutable_enum_value](../../examples/step_20_dictionaries/43_mutable_enum_value.py) | [Notebook](../../examples/step_20_dictionaries/43_mutable_enum_value.ipynb) |
| validator wrong type | [41_validator_wrong_type](../../examples/step_20_dictionaries/41_validator_wrong_type.py) | [Notebook](../../examples/step_20_dictionaries/41_validator_wrong_type.ipynb) |

## Boundaries

An input schema checks the shape of a reference; runtime validation resolves its code. Dictionary properties use the supported immutable annotations. Lifecycle status properties have a separate contract.

The completed-value check still accepts two invalid after-validator results: a value outside a `Literal` choice and `None` for a non-nullable union. These are defects, not supported declaration forms. Preserve both constraints in user validators.

See [validation and export](../how-to/dictionary-validation-and-export.md), [relations and specializations](step-21-relations.md#generalization-and-specialization), and [entity invariants](../reference/intents-and-invariants.md).
