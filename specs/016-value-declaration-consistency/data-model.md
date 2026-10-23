# Data Model: the declaration, the declared value, its reference form and its two schemas

**Feature**: `specs/016-value-declaration-consistency` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md)

The model has six things: a declaration, the placeholder it produces, the declared value it becomes, the reference form that value exports, the pair of JSON schemas for that form, and the diagram rows built from it. Nothing is persisted differently; the graph keeps the shape #243 merged.

## Declaration

One authored line inside a kind's class body.

| Aspect | Rule |
| --- | --- |
| Form | `NAME = value(**fields)` — the only declaration form for both kinds |
| Name | an uppercase class attribute; it becomes an instance of the declaring type |
| Fields | `code` and `display_name` from the kind (required, non-blank) plus the model's own fields |
| Import | `from aoa.action_machine.domain import value` |
| Result at runtime | a `ValueSpec` placeholder, replaced after the class is created |
| Removed form | `NAME = TheClass(...)` — the class name does not exist while its body runs, so the line fails; no alias remains |

## Placeholder

What `value(...)` returns before the class exists.

| Aspect | Rule |
| --- | --- |
| Type | `ValueSpec`, holding the keyword arguments verbatim |
| Visibility | internal; no consumer holds, stores or compares one |
| Never a field | both kind markers declare `ignored_types=(ValueSpec,)`, so the class body does not create a model field |
| Lifetime | from the line's execution to `__pydantic_init_subclass__` of the class being created |

## Declared value

A validated, shared instance of a declaring kind — a dictionary value or a state status — produced from the placeholder. The two kinds share the declaration machinery; the reference form, the exported payloads and the property-type rule belong to the dictionary kind only, which is why the rows below name it.

| Aspect | Rule |
| --- | --- |
| Identity | `(dictionary type, code)`; the attribute name in the body is where it is reachable |
| Construction | `__pydantic_init_subclass__` calls `cls(**spec.kwargs)` after the model exists; defaults apply, unknown keys are refused |
| Catalogue | `members` (tuple, declaration order), `codes()`, `by_code(code)`, `entity_type` — unchanged by this feature |
| Immutability | the model is frozen; a **dictionary** value's extra fields are limited to the supported types below, so nested data cannot be mutated either; a status keeps its fields as they are |
| Sharing | the same object for every consumer; `by_code` and the attribute are identical |
| Inheritance | a dictionary does not inherit values; a state type inherits its parent's catalogue |

## Supported property types

The extra fields a **dictionary** value may declare, checked recursively at class creation.

| Accepted | Refused |
| --- | --- |
| `str`, `int`, `float`, `bool` | `list`, `dict`, `set`, `frozenset` |
| `Decimal`, `date`, `datetime`, `time` | a nested Pydantic model or any other class |
| `UUID`, `Enum` subclass, `Literal[...]` | `Any`, `object` |
| `tuple[...]` of accepted types | a container holding a refused type, at any depth |
| `Optional[X]` / `X \| None` where `X` is accepted | — |

Statuses do not carry this rule: the state kind's switch is off, because a status may hold data that need not be hashable and may hold a value with no JSON form — both are existing, tested lifecycle scenarios.

## Reference form

What a consumer receives: `to_reference()` and the model's plain serializer both produce it.

```json
{"code": "eur", "display_name": "Euro", "properties": {"symbol": "€", "since": "02/01/2020"}}
```

| Aspect | Rule |
| --- | --- |
| Mode | the value's **JSON** export (`model_dump(mode="json")`); there is no Python-native variant |
| Serializers | a `@field_serializer` on an extra field is applied; its output is what a consumer sees |
| Standard types | a `date` becomes its JSON string; a tuple becomes a JSON array; a `Decimal` becomes its JSON string |
| Leaves | JSON values only — `json.dumps(to_reference())` never raises |
| Nesting | guarded by construction: no nested model and no mutable container can exist, so the form has no second hop |
| Equality with Python mode | may differ (a Python-mode dump can hold a `date`); the reference never does, and the pages say so |
| Resolution on read | the `code` is authoritative; `display_name` and `properties` in an incoming payload are ignored |

## The two schemas

One field type, two contracts.

| Mode | `required` | `properties` | Extra keys |
| --- | --- | --- | --- |
| validation | `["code"]` | member of type `object`, content unconstrained because the runtime ignores it | refused (`additionalProperties: false`) |
| serialization | `["code", "display_name", "properties"]` | each declared extra field by name, with its **emitted** JSON type (a serializer's type, not the Python field's), `additionalProperties: false` | refused |

```json
// validation
{"type": "object", "additionalProperties": false, "required": ["code"],
 "properties": {"code": {"type": "string", "minLength": 1},
                "display_name": {"type": "string", "minLength": 1},
                "properties": {"type": "object"}}}

// serialization
{"type": "object", "additionalProperties": false,
 "required": ["code", "display_name", "properties"],
 "properties": {"code": {"type": "string", "minLength": 1},
                "display_name": {"type": "string", "minLength": 1},
                "properties": {"type": "object", "additionalProperties": false,
                               "properties": {"symbol": {"type": "string"},
                                              "since": {"type": "string"}}}}}
```

| Aspect | Rule |
| --- | --- |
| Mode source | `handler.mode`, published by `GetJsonSchemaHandler` |
| Output member types | generated from the class's own serialization schema, so a serializer that changes a type changes the schema |
| References | none: the supported set produces no `$defs`; a test asserts it |
| Asymmetry | intentional; documented in the contract |

## ERD payload and card

| Aspect | Rule |
| --- | --- |
| Graph reference | `{code, display_name, properties: {...}}` — unchanged |
| Payload entity value | `{code, display_name, properties: [{name, value}, …]}` |
| Each item | `name` and `value` are strings; no additional members |
| Text form | a string property is display text; a number, boolean or array is `json.dumps` of it with `ensure_ascii=False` |
| Escaping | names and values are HTML-escaped once, inside the existing value row |
| Empty | a value with no extra properties renders code and label, no empty row |
| Vocabulary | the renderer names no dictionary, kind or field |

## Group label

| Aspect | Rule |
| --- | --- |
| Owner | the server composes `field (by Dictionary)` |
| Payload | `label` carries the full text; `dictionary_label` no longer exists in the group shape |
| Client | renders `label` as received, escaping once; appends nothing |
| Degradation | a group with no label falls back to its id; never `(by )` |

## Rules and where they are enforced

| Rule | Enforced at | Requirement |
| --- | --- | --- |
| A declaration uses `value(...)` and nothing else | import time (a class body that names its own class fails) | FR-001, FR-003 |
| Only declared fields, valid data | class creation, Pydantic validation | FR-005 |
| Duplicate code refused | `__pydantic_init_subclass__` | FR-005 |
| Empty concrete dictionary refused | `@entity` decorator, `_require_declared_values` | FR-006 |
| Catalogue rules per kind | `__pydantic_init_subclass__`, the kind switches | FR-006 |
| Refused property type | `__pydantic_init_subclass__`, dictionary kind only | FR-010, FR-011 |
| Frozen instance | model config, unchanged | FR-012 |
| Serializers honoured | `to_reference()` via JSON-mode dump | FR-013 |
| JSON-only leaves | the same call, plus D4's type set | FR-014 |
| Input schema | `__get_pydantic_json_schema__`, validation branch | FR-017 |
| Output schema | the same hook, serialization branch | FR-018 |
| Runtime code resolution | `normalize()` in the core schema, unchanged | FR-019 |
| Property carrier | `ListEntitiesAction` + payload schema, unchanged | FR-021 |
| Label composed once | server SQL, client renderer | FR-027 |
