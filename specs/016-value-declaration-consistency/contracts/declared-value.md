# Contract: explicit declarations and dictionary references

**Feature:** #244 · [Plan](../plan.md) · [Dictionary card](dictionary-card.md)

This page describes the implemented behavior. The tutorial in
[Closed dictionaries](../../../docs/tutorials/step-20-dictionaries.md) introduces the
concepts and links each experiment to a runnable script and notebook.

## Declaration and catalogue

```python
from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe the supported currency."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


assert CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR
```

`value` records keyword arguments in a placeholder. After the model class exists, its
hook constructs validated instances and populates the catalogue. Defaults and field
validators apply; unknown constructor arguments are refused. This hook remains
automatic, but the class namespace no longer substitutes a factory for its own name.
An old constructor-looking declaration follows normal Python lookup: an unbound name
raises NameError, while an existing outer binding can resolve to a different object.

`BaseStateEntity` uses the same declaration factory. `members`, `codes()`, `by_code()`
and `entity_type` keep their existing meanings. Codes are unique and nonblank; the
catalogue keeps declaration order. A dictionary subclass owns its own catalogue;
an undecorated intermediate can be empty, while `@entity` requires at least one value.
A state subclass without new declarations can inherit its parent's catalogue.

If a class assigns a field named `value`, use `from aoa.action_machine.domain import
value as declared` and call `declared(...)` in that body. A plain annotation without an
assignment does not itself bind a Python local name.

## Dictionary property annotations

Accepted types are `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `time`,
`UUID`, an Enum subclass, Literal, unions of accepted types (including None) and tuples
of accepted types. The check recurses through tuples and unions. `list`, `dict`, `set`,
`frozenset`, `Any`, `object`, arbitrary classes and nested models are rejected.

This is a supported-type policy, not a universal proof of deep immutability. The current
hook inspects annotations; it does not recheck a custom validator's returned object or
recursively inspect Enum member internals. Validators must preserve their declared types.
The refusal names the dictionary class, the field and the unsupported type, including
an unsupported type nested inside a tuple; it does not report a nested index path.

The policy applies to dictionaries only. State properties retain their existing freedom.
Frozen models refuse attribute reassignment but do not recursively freeze a status list.

## Input and reference export

A dictionary field accepts its declared instance or a reference mapping whose code
selects a member. The label and properties in an incoming mapping do not override the
declaration. The only permitted top-level keys are code, display_name and properties.
Bare strings, missing/blank/unknown codes and copied or foreign instances are refused.
An optional reference can be None. Constructing a separate instance does not register it.

`to_reference()` is `model_dump(mode="json")`. Its outer shape is
`{code, display_name, properties}`; additional fields appear under properties after
Pydantic applies field serializers. Ordinary `model_dump()` uses Python mode and may
retain native values, unless a serializer transforms them in that mode too. A serializer
with `when_used="json"` applies only to the JSON path.

Dates, times and UUIDs become strings; Decimal becomes a string; tuples become arrays.
The output may contain mutable dictionaries and lists: those are payload containers,
not mutable fields of the declared value. Editing an exported array made from a tuple
does not modify the catalogue member or a later export. Custom serializer outputs must
be JSON-serializable; unsupported return values can still raise an export error.

## Validation and serialization schemas

| Mode | Required top-level keys | Descriptive properties |
| --- | --- | --- |
| validation | code | Optional label and open properties object |
| serialization | code, display_name, properties | Named property schemas with their emitted types; unknown keys forbidden |

Both schemas reject unknown top-level keys. The output describes a field serializer's
return type rather than blindly copying the original Python annotation. The nested
output properties currently have no required list, even though the ordinary full export
includes the fields. Input schema validation checks structure; runtime additionally
checks membership and whitespace-only codes. The schema constrains the types of optional
label/properties fields, while runtime lookup ignores their contents.

Known limitation: generating a serialization schema for an Enum property currently
raises KeyError for its `#/$defs/...` reference because the extracted schema loses the
definition. Successful dictionary construction and JSON export do not prove this schema
path works. Scalar/tuple properties and the documented date-to-string serializer cases
are covered separately.

## Verification

The branch's tests cover the public factory and catalogue, supported/refused property
annotations, reference lookup and serializers, validation/output schemas, graph JSON
and ERD payloads. The documentation examples additionally isolate tuple export
independence, the factory alias, each unsupported annotation and the difference between
status and dictionary property rules. The existing tests do not establish the stronger
custom-validator or Enum-schema guarantees noted as limitations above.
