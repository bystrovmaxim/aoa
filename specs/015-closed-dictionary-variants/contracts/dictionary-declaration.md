> Current declaration and export updates: #244 replaces class-name declarations with
> `value(...)`, restricts dictionary property annotations, applies field serializers in
> JSON references and separates validation/output schemas. See the
> [current contract](../../016-value-declaration-consistency/contracts/declared-value.md).

# Contract: declaring a closed dictionary and referencing its values

**Feature**: `specs/015-closed-dictionary-variants` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md)

This contract is what a model author writes and what a consumer of the graph reads. It is asserted by the tests named at the end.

## 1. The declaration surface

```python
@entity(description="Currency reference value", domain=DictionariesDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    symbol: str = Field(description="Currency symbol")

    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")
    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")
```

Guarantees:

1. `code` and `display_name` come from the kind and are required and non-blank; the model declares only its own additional fields.
2. Inside the body, the class's own name resolves to the internal declaration factory only in the call form; any other unknown name still raises `NameError`, and a self-referential annotation stays a forward reference.
3. After the class is created, each declared name is an instance of the class with every field initialised, defaults applied, and unknown keys refused.
4. `members` is the tuple of declared values in declaration order; `codes()` is their codes; `by_code(code)` returns the declared value and raises `KeyError` otherwise; `entity_type` is the class.
5. Codes are compared exactly and are free-form non-blank strings; the demo writes them lowercase.
6. Values are not inherited: a subclass declares its own set and starts with an empty catalogue.
7. A decorated dictionary with no values is refused; an undecorated intermediate class with no values is accepted.
8. A duplicate code inside one dictionary is refused at class creation; a copy built by hand is not a declared value anywhere.

## 2. The reference surface

```python
class BillingSliceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Slice id")
    currency: CurrencyEnumEntity = Field(description="Money unit")
    settlement_currency: CurrencyEnumEntity | None = Field(default=None, description="Optional unit")
```

| Input | Result |
| --- | --- |
| `CurrencyEnumEntity.USD` | accepted; the field holds that value |
| `{"code": "usd", "display_name": "…", "properties": {…}}` | accepted; resolved by `code` to the declared value, the rest ignored |
| `"usd"` | refused: a bare code never enters the model; the resource resolves it first |
| `{"code": "bootleg", …}` | refused: `'bootleg' is not a declared value of CurrencyEnumEntity. Declared: ['usd', 'eur', 'rub']` |
| `CurrencyEnumEntity(code="usd", display_name="Copy", symbol="?")` | refused: a copy is not a declared value; use `CurrencyEnumEntity.USD` |
| absent, on an optional field | `None` |
| a mapping without `code` | refused as malformed |

Serialization of a field: `{"code": "...", "display_name": "...", "properties": {...extra declared fields...}}`. Reading is driven by `code`; `display_name` and `properties` in the payload are cargo for consumers that do not hold the model and never change behaviour.

## 3. The graph surface

- The dictionary's `Entity` node carries `entity_kind: "enum"` and `properties.values`, an array of `{code, display_name, properties}`; the schema requires it when the kind is `enum`.
- A referencing field's `EntityField` row carries `reference_qualname`, the dictionary's interchange id.
- Values are not nodes and have no domain edges of their own.
- A graph exported before this contract lacks `values`; it is rebuilt rather than versioned, as was the case for `entity_kind` in #239.

## 4. Refusals and their messages

| Case | Error | Message names |
| --- | --- | --- |
| decorated dictionary with no values | `ValueError` | the class and the missing declaration |
| duplicate code | `ValueError` | the class and the duplicate code |
| blank `code` or `display_name` | Pydantic `ValidationError` | the class and the field |
| undeclared code on assignment or read | Pydantic `ValidationError` | the field, the code, the declared codes |
| constructed copy | Pydantic `ValidationError` | the field and the declared value to use |
| payload without `code` | Pydantic `ValidationError` | the field |
| field typed by an intermediate dictionary with no values | `ValidationError` at first use, `SpecializationDeclarationError` when it classifies an axis | the class and the type |

## 5. Tests that assert this contract

- `packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py` — the kind word, the suffix, the declaration surface.
- `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py` — the five input shapes, serialization, the code-authoritative read.
- `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_scope.py` — non-inheritance, the empty decorated dictionary, duplicates.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py` — `reference_qualname`, `values` in the schema.
- The demo's own tests — the dictionary node, the references, the values.

## Current ERD representation

The graph still keeps a value's extra fields under `properties` as an object. Maxitor's
ERD response converts that object to `properties: [{"name": "symbol", "value": "€"}]`;
its strict schema declares both item fields and forbids additional keys. The card displays
the escaped name/value text inside the value row. This was implemented in PR #243, and
#244 verifies it after the serialization changes. The earlier proposal to add
`properties_json` is superseded. Specialization group labels are supplied complete by the
server and rendered once; `dictionary_label` is no longer part of the ERD group payload.
