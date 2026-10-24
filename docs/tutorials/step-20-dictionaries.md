# Closed dictionaries: declare values and use references

A dictionary declares the allowed reference values in its class body. Use the imported `value(...)` factory for each member. A typed reference resolves a code to a declared member. Export includes the code, human label and serialized properties.

## Migrate an existing declaration

Keep the dictionary's declared values and exported reference payloads. Replace bare entity selection fields with `Annotated[AssociationOne[D], NoInverse()] = Field(description="...")` and Python member arguments with `AssociationOne(id=member.code, entity=member)`. Custom validators must return values consistent with their annotations: completed members are now checked after validation, rather than relying only on the annotation. A tuple property cannot be replaced by a list. The exact refusal appears below.

Serialization schemas now retain the definitions needed by enum properties. Regenerate output schemas with `mode="serialization"`. Every emitted nested property is required, including null-valued properties; excluded properties are absent. Standalone dictionary validation schemas still accept a code-only reference. Entity selections require an explicit association and an id-only JSON input.

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

The following `Holder(BaseModel)` is a plain DTO. Entity hosts use the complete association shown below; their serialization schema has a separate documented limitation.

The following `Holder(BaseModel)` is a plain DTO. Entity hosts use the complete association shown below; their serialization schema has a separate documented limitation.

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
| validator wrong type | [41_validator_wrong_type](../../examples/step_20_dictionaries/41_validator_wrong_type.py) | [Notebook](../../examples/step_20_dictionaries/41_validator_wrong_type.ipynb) |
| validator nested list | [42_validator_nested_list](../../examples/step_20_dictionaries/42_validator_nested_list.py) | [Notebook](../../examples/step_20_dictionaries/42_validator_nested_list.ipynb) |
| mutable enum value | [43_mutable_enum_value](../../examples/step_20_dictionaries/43_mutable_enum_value.py) | [Notebook](../../examples/step_20_dictionaries/43_mutable_enum_value.ipynb) |
| literal choices | [44_literal_choices](../../examples/step_20_dictionaries/44_literal_choices.py) | [Notebook](../../examples/step_20_dictionaries/44_literal_choices.ipynb) |
| union nullability | [45_union_nullability](../../examples/step_20_dictionaries/45_union_nullability.py) | [Notebook](../../examples/step_20_dictionaries/45_union_nullability.ipynb) |
| tuple item validation | [46_tuple_item_validation](../../examples/step_20_dictionaries/46_tuple_item_validation.py) | [Notebook](../../examples/step_20_dictionaries/46_tuple_item_validation.ipynb) |
| property declarations | [47_property_declarations](../../examples/step_20_dictionaries/47_property_declarations.py) | [Notebook](../../examples/step_20_dictionaries/47_property_declarations.ipynb) |

The four completed-value scenarios group refusals with their accepted neighbors: literal choices, union nullability, tuple items and property declarations. Each notebook keeps the cases as separate steps within the same scenario.

## Boundaries

An input schema checks the shape of a reference; runtime validation resolves its code. Dictionary properties use the supported immutable annotations. Lifecycle status properties have a separate contract.

The completed-value check reads the whole annotation. A value outside its `Literal` choices and `None` for a union that excludes it are refused, as is `bool` where `int` is declared. A leaf keeps its exact type, so an `int` is not a `float` and a `datetime` is not a `date`; input given to the declaration is still coerced first, so `ratio: float` with `1` holds `1.0`. For accepted neighbors, use a declared literal choice, a member of the union, an explicitly nullable union or literal, or a value of the declared type. A property annotated only `None` is refused; tuple diagnostics identify the failing item. See [the complete migration and exact outputs](../how-to/dictionary-validation-and-export.md#migrate-completed-values).

See [validation and export](../how-to/dictionary-validation-and-export.md), [relations and specializations](step-21-relations.md#generalization-and-specialization), and [entity invariants](../reference/intents-and-invariants.md).

## Follow a dictionary reference

An entity selection is a complete association. Use an explicit wrapper in Python, or an id-only object in JSON. The canonical member is resolved from its code. Export remains a code/display_name/properties reference; the input and output formats differ.

[Script](../../examples/step_20_dictionaries/56_selection_transport.py) · [Executed notebook](../../examples/step_20_dictionaries/56_selection_transport.ipynb)

```python
"""Select canonical dictionary values in Python and JSON, then export references.
Run: .venv/bin/python examples/step_20_dictionaries/56_selection_transport.py
"""

from typing import Annotated

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class SelectionDomain(BaseDomain):
    """Group the selection declarations."""

    name = "selection"
    description = "Dictionary selection transport"


@entity(description="Currency", domain=SelectionDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shared currency values."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="Price selection", domain=SelectionDomain)
class PriceCoreEntity(BaseCoreEntity):
    """Require a selection while permitting explicit absence."""

    currency: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(description="Currency")


def python_selection() -> None:
    """Resolve a wrapper to the canonical shared member."""
    original = AssociationOne(id="eur")
    price = PriceCoreEntity(currency=original)
    assert price.currency is not original
    assert price.currency.entity is CurrencyEnumEntity.EUR
    assert price.currency.is_loaded and original.entity is None
    print("Python selection:", price.currency.id, price.currency.symbol)
    try:
        PriceCoreEntity(currency=CurrencyEnumEntity.EUR)
    except ValidationError as error:
        assert error.errors()[0]["type"] == "is_instance_of"
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A raw member was accepted")


def json_selection() -> None:
    """Use the JSON input shape and explicit nullability."""
    price = PriceCoreEntity.model_validate_json('{"currency":{"id":"eur"}}')
    assert price.currency.entity is CurrencyEnumEntity.EUR
    assert PriceCoreEntity.model_validate_json('{"currency":null}').currency is None
    payload = price.model_dump(mode="json")
    assert payload == {"currency": {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}}
    print("JSON export:", payload)
    try:
        PriceCoreEntity.model_validate_json(price.model_dump_json())
    except ValidationError as error:
        assert (
            error.errors()[0]["msg"]
            == "Value error, a dictionary association JSON input is an object with exactly one 'id' key."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("Exported reference was accepted as selection input")


def schema_modes() -> None:
    """Compare the transport schemas without claiming typed export properties."""
    validation = PriceCoreEntity.model_json_schema(mode="validation")["properties"]["currency"]["anyOf"][0]
    serialization = PriceCoreEntity.model_json_schema(mode="serialization")["properties"]["currency"]["anyOf"][0]
    assert validation["required"] == ["id"]
    assert validation["additionalProperties"] is False
    assert serialization["required"] == ["code", "display_name", "properties"]
    print("Input keys:", validation["required"])
    print("Output keys:", serialization["required"])


def main() -> None:
    """Run Python selection, JSON transport and schema modes."""
    python_selection()
    json_selection()
    schema_modes()


if __name__ == "__main__":
    main()
```

Actual output:

```text
Python selection: eur €
ValidationError: 1 validation error for PriceCoreEntity
currency
  Input should be an instance of AssociationOne [type=is_instance_of, input_value=CurrencyEnumEntity(code='...me='Euro', symbol='€'), input_type=CurrencyEnumEntity]
    For further information visit https://errors.pydantic.dev/2.12/v/is_instance_of
JSON export: {'currency': {'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': '€'}}}
ValidationError: 1 validation error for PriceCoreEntity
currency
  Value error, a dictionary association JSON input is an object with exactly one 'id' key. [type=value_error, input_value={'code': 'eur', 'display_...ies': {'symbol': '€'}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
Input keys: ['id']
Output keys: ['code', 'display_name', 'properties']
```

The graph carries an ordinary single association and retains the field row and dictionary hint. Nullable selections have the same graph cardinality. Collections of dictionary values need a separate link model. See the [declaration and transport guide](../how-to/dictionary-references.md), [graph script](../../examples/step_20_dictionaries/08_graph.py) and [notebook](../../examples/step_20_dictionaries/08_graph.ipynb). The [verification report](../reports/complete-relationship-verification.md) records the current association-schema and Maxitor limitations.
