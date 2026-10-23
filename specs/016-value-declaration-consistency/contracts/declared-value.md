# Contract: declaring a value, and what a consumer may do with it

**Feature**: `specs/016-value-declaration-consistency` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

This is what a model author writes, what a consumer receives, and what the two JSON schemas say. It is asserted by the tests named at the end.

## 1. The declaration surface

```python
from aoa.action_machine.domain import BaseEnumEntity, value

class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the supported currencies."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")
```

```python
from aoa.action_machine.domain import BaseStateEntity, value

class OrderStateEntity(BaseStateEntity):
    """Declare order statuses and their properties."""

    requires_receipt: bool
    NEW = value(code="new", display_name="New", requires_receipt=False)
    PAID = value(code="paid", display_name="Payment received", requires_receipt=True)
```

Guarantees:

1. `value` is imported from `aoa.action_machine.domain`; it is the only declaration form for both kinds.
2. `value(...)` returns an internal placeholder. All arguments are keyword arguments and are passed to the class's own constructor after the class exists.
3. After class creation every declared name is an instance of the declaring type, with defaults applied and unknown keys refused; the class name itself never resolves inside its body, so the replaced form fails at the line that writes it.
4. `members`, `codes()`, `by_code()`, `entity_type`, declaration order, the duplicate refusal and each kind's inheritance and empty-catalogue rules are unchanged.
5. The conversion of placeholders into instances stays automatic and happens once per class; it is documented as the one remaining automatic step.
6. A declaring class body cannot also bind the name `value`: an annotation such as `value: Opaque = Field(...)` shadows the factory for the lines that follow. A model that needs a field called `value` on a declaring kind imports the factory under another name — `from aoa.action_machine.domain import value as declared` — and declares with that name; the test `test_a_field_named_value_needs_the_factory_under_another_name` proves the escape hatch.

## 2. Which properties a dictionary value may declare

The supported set is immutable and enforced at class creation:

| Accepted | Refused |
| --- | --- |
| `str`, `int`, `float`, `bool` | `list`, `dict`, `set`, `frozenset` |
| `Decimal`, `date`, `datetime`, `time` | a nested model or any other class |
| `UUID`, `Enum` subclass, `Literal[...]` | `Any`, `object` |
| `tuple[...]` of accepted types | a container holding a refused type at any depth |
| `Optional[X]` / `X \| None` where `X` is accepted | — |

The rule binds the **dictionary** kind. A state type keeps its present freedom, because a status may carry data that need not be hashable and a value with no JSON form — both are existing lifecycle scenarios.

## 3. Immutability

| Attempt | Result |
| --- | --- |
| `CurrencyEnumEntity.EUR.display_name = "Changed"` | refused by the frozen model (`ValidationError`), as today |
| mutating a container under `to_reference()["properties"]` | no such container exists: refused types never enter the class |
| mutating a tuple's content | tuples are immutable |
| mutating a nested mapping | no nested mapping exists |

A copy — shallow or deep — is not used as the protection: the declared value carries no mutable data at all.

## 4. The reference form

```python
CurrencyEnumEntity.EUR.to_reference()
# {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}
```

| Rule | Statement |
| --- | --- |
| Mode | the value's JSON export; there is no Python-native variant |
| Serializer | `@field_serializer` on an extra field is applied; its return value is what a consumer sees |
| Standard types | `date` → `"2020-01-02"` (or the serializer's text), `Decimal` → `"9.99"`, tuple → `["a", "b"]` |
| Leaves | JSON values only; `json.dumps(value.to_reference())` never raises |
| Python mode | `model_dump()` may differ — a `date` stays a `date` there — and the pages say so |
| Read side | the `code` is authoritative; a payload's `display_name` and `properties` are ignored |

## 5. The two JSON schemas

For a dictionary-typed field, `model_json_schema(mode="validation")` describes what is accepted and `mode="serialization"` describes what is emitted.

| Input | Validation schema | Runtime |
| --- | --- | --- |
| `{"code": "eur"}` | accepted | resolves to the declared value |
| `{"code": "eur", "display_name": "Euro"}` | accepted | resolved by code, label ignored |
| `{"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}` | accepted | resolved by code, properties ignored |
| `{"display_name": "Euro"}` | refused (no `code`) | refused as malformed |
| `{"code": ""}` | refused (`minLength: 1`) | refused: a blank code |
| `{"code": "eur", "extra": 1}` | refused (`additionalProperties: false`) | refused: only `code`, `display_name`, `properties` |
| `"eur"` | refused (a string is not an object) | refused: a bare code never enters the model |

The output schema additionally requires `display_name` and `properties`, and types each extra property by its **emitted** JSON type — a field with a serializer returning `str` is `{"type": "string"}`, not a date with `format`.

## 6. Refusals and their messages

| Case | Error | Message names |
| --- | --- | --- |
| a list, dict or set property | `ValueError` at class creation | the class, the field, the refused type, the supported set |
| a refused type nested in a tuple | the same, at class creation | the same, with the nested position |
| a mutable property on a **state** type | accepted — the rule does not bind this kind | — |
| duplicate code | `ValueError` (unchanged) | the class, the duplicated code |
| an empty concrete dictionary | `ValueError` from the decorator (unchanged) | the class, its noun, what to do |
| a blank `code` or `display_name` | `ValidationError` (unchanged) | the field |
| an unknown field in a declaration | `ValidationError` (unchanged) | the field |
| a bare code in a field | `ValueError` (unchanged) | the class, the accepted forms |
| an undeclared code in a reference object | `ValueError` (unchanged) | the code, the class, the declared codes |

## 7. Tests that assert this contract

| Test | Covers |
| --- | --- |
| `tests/action_machine/domain/test_declared_values.py` | the factory, the conversion, the catalogue, the kind switches — rewritten without the alias |
| `tests/action_machine/domain/test_value_export.py` | `value` is a public import, and the alias is gone from the package |
| `tests/action_machine/domain/test_dictionary_scope.py` | non-inheritance, empty dictionary, the reference form's shape |
| `tests/action_machine/domain/test_dictionary_core_schema.py` | accepted inputs, refusals, JSON-mode serialization |
| `tests/action_machine/domain/test_dictionary_property_types.py` (new) | every accepted type; every refused type, at top level and nested; a status keeping its freedom |
| `tests/action_machine/domain/test_dictionary_json_schema.py` (new) | the two modes, a serializer's type in output, no `$defs`, no recursion |
