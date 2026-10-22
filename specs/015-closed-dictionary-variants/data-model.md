# Data Model: a closed dictionary and the axis that borrows it

**Feature**: `specs/015-closed-dictionary-variants` | **Date**: 2026-10-22 | **Plan**: [plan.md](./plan.md)

The model has five kinds of thing: the dictionary, its values, the catalogue, a reference from a field, and an axis that borrows the set. The graph is the projection of all five; nothing new is persisted.

## Dictionary

A class of the `enum` kind. It is an ordinary entity — it has a domain, a name with the kind's suffix, and declared fields — plus a closed set of values it declares itself.

| Aspect | Rule |
| --- | --- |
| Declaration | `@entity` class inheriting `BaseEnumEntity`; values declared in the class body |
| Fields from the kind | `code: str` and `display_name: str`, both required and non-blank |
| Fields from the model | any additional fields; defaults apply; unknown keys refused |
| Values | at least one for a decorated dictionary; an undecorated intermediate class may be empty |
| Uniqueness | codes unique inside one dictionary; duplicates refused at class creation |
| Inheritance | values are **not** inherited; a subclass declares its own set and starts empty |
| Immutability | values are frozen instances, shared by every reference |
| Lifecycle | none; a dictionary is not a process position |
| Graph | one `Entity` node with `entity_kind: "enum"` and `properties.values` |

```python
@entity(description="Currency reference value", domain=DictionariesDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    symbol: str = Field(description="Currency symbol")

    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")
    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")
    RUB = CurrencyEnumEntity(code="rub", display_name="Ruble", symbol="₽")
```

## Value

One immutable instance of a dictionary, identified inside it by `code`.

| Aspect | Rule |
| --- | --- |
| Identity | `(dictionary type, code)`; the same code in two dictionaries is two different values |
| Label | `display_name`, non-blank, what diagrams show |
| Extra data | the dictionary's additional fields, carried under `properties` on the wire |
| Construction | the class body declares the values; a hand-built copy is constructible, but it is not a declared value, so a dictionary-typed field refuses it |
| Collection | `members` (tuple, declaration order), `codes()` (list), `by_code(code)` (raises `KeyError`), `entity_type` |

## Catalogue

The dictionary's own set, exposed as class API and readable without an instance.

| Member | Type | Behaviour |
| --- | --- | --- |
| `members` | `tuple[DictionaryType, ...]` | declared values, declaration order; empty for an undecorated intermediate |
| `codes()` | `list[str]` | `code` of every member, declaration order |
| `by_code(code)` | `DictionaryType` | the declared value; `KeyError` for an unknown code |
| `entity_type` | `type[DictionaryType]` | the declaring class |

## Reference

A field typed by a dictionary. It is not an ownership relation and adds no edge of its own.

| Aspect | Rule |
| --- | --- |
| Type | the dictionary class, optionally `| None`; `Annotated[...]` is unwrapped when the type is detected |
| Accepted input | a declared value, or its reference object `{code, display_name, properties}` |
| Refused input | a bare code string; a reference object with an undeclared code; a constructed copy; a value of another dictionary |
| Held value | the declared instance, by identity |
| Serialized form | `{"code", "display_name", "properties": {…extra fields…}}` |
| Read rule | the `code` is authoritative; the other fields are not used and not compared |
| Absent value | `None` only, and only where the field is optional; a payload without `code` is malformed |
| Graph | the hosting `EntityField` row gains `reference_qualname` = the dictionary's interchange id |

```python
class BillingSliceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Slice id")
    currency: CurrencyEnumEntity = Field(description="Money unit")
```

## Axis

A head's `Specialization[Alternatives, Dictionary]` field plus, per extension, a `Generalization[…]` field whose `Classifier` names that field and the declared value the extension is. There is no classifier field.

| Part | Rule |
| --- | --- |
| Head field | `Specialization[A | B, Dictionary]`; optional as `| None` when a row may have no variant |
| Head marker | none: the type argument names the dictionary, so a `Classifier` on the head is refused |
| Extension marker | `Classifier(field="record", variant=EditionKindEnumEntity.FIRST)` — the field that points back and a declared value of that dictionary |
| Extension attribute | `declared_variant` — derived from its own marker at class creation |
| Container value | `variant` holds a declared value or its reference object; a bare code is refused |
| Pairing | a container refuses a value that disagrees with the class of its hydrated `entity` |
| Coverage | every declared value has exactly one alternative; every alternative's declared value is in the catalogue |
| Copy | an equal-but-distinct value is refused; the message names `Type.VALUE` |
| Sharing | one dictionary may classify several axes; each is checked for full coverage |
| `Literal` | refused for specialization codes; it stays for non-dictionary closed sets |
| Graph | one `entity_specialization` edge per alternative, in the dictionary's declaration order, carrying the code and the dictionary |

## Graph rows

The interchange document is the contract with Maxitor; these are the rows the change adds or extends.

```json
{"id": "shop.model.CurrencyEnumEntity", "type": "Entity", "label": "CurrencyEnumEntity",
 "properties": {"description": "Currency reference value", "entity_kind": "enum",
   "values": [
     {"code": "usd", "display_name": "US dollar", "properties": {"symbol": "$"}},
     {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}
   ]}}

{"id": "shop.model.BillingSliceCoreEntity", "type": "Entity", "label": "BillingSliceCoreEntity",
 "properties": {"description": "Slice", "entity_kind": "core"}}

{"id": "shop.model…:currency", "type": "EntityField", "label": "currency",
 "properties": {"field_type": "CurrencyEnumEntity", "primary_key_hint": false,
                "reference_qualname": "shop.model.CurrencyEnumEntity"}}

{"relationship": "specialization",
 "properties": {"field_name": "kind",
                "classifier_value": "first",
                "dictionary_qualname": "shop.model.EditionKindEnumEntity",
                "dictionary_label": "Edition kind"}}
```

## Validation rules

| # | Rule | Where | Error |
| --- | --- | --- | --- |
| 1 | A decorated dictionary declares at least one value | class creation | `ValueError` naming the class |
| 2 | Codes are unique inside a dictionary | class creation | `ValueError` naming the duplicate |
| 3 | `code` and `display_name` are non-blank | class creation | Pydantic `ValidationError` naming the field |
| 4 | A field accepts only a declared value or its reference object | assignment / read | `ValidationError` naming the field, the code and the declared codes |
| 5 | A bare code string is refused by a dictionary-typed field | assignment / read | Pydantic `ValidationError` naming the expected reference object |
| 6 | A constructed copy is refused | assignment / read | `ValidationError` naming the declared value to use |
| 7 | A payload without `code` is malformed | read | `ValidationError` naming the field |
| 8 | A container's `variant` and the class of its `entity` agree | container construction | Pydantic `ValidationError` naming both values |
| 9 | The head field's second type argument is a non-empty, decorated dictionary | graph build | `SpecializationDeclarationError` naming the head and the field |
| 10 | A head-side `Classifier`, a separate classifier field or a `Literal` is refused | graph build | `SpecializationDeclarationError` naming the single declaration form |
| 11 | An extension's `field` is a `Generalization[…]` of that head | graph build | `SpecializationDeclarationError` naming the extension and the field |
| 12 | Every declared value has an alternative | graph build | `SpecializationDeclarationError` naming the uncovered code |
| 13 | Every alternative declares a value of the axis dictionary, and it is the declared object | graph build | `SpecializationDeclarationError` naming the extension and the code |
| 14 | An extension's value is the declared instance, not a copy | graph build | `SpecializationDeclarationError` naming `Type.VALUE` |
| 15 | An `enum` node carries `values` | graph document validation | `jsonschema` failure naming the node |
| 16 | An undeclared code in storage is refused before the model is built | resource read | the resource's domain error naming the row, the field, the code and the declared set |

## State transitions

Not applicable: a dictionary has no lifecycle, and a value never changes. A reference changes only by pointing at another declared value; the set itself changes only by a code change.
