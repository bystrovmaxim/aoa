# Research: an explicit `value(...)` declaration and a declared value that keeps its contract

**Feature**: `specs/016-value-declaration-consistency` | **Date**: 2026-10-23 | **Baseline**: `e791ad28` | **Plan**: [plan.md](./plan.md)

Every number below was measured on the baseline, not estimated. Where a decision needed a prototype, the prototype was run with the repository's own environment (`.venv`, Pydantic 2.12.5) and its output is quoted.

## Measured baseline

| Fact | Number | How measured |
| --- | --- | --- |
| Class-name declarations to migrate | 373 in 116 files — 270 in 91 files outside the demo, 103 in 25 demo files | `evidence/scan_value_declarations.py`, an AST walk over class bodies whose base name ends in `EnumEntity`/`StateEntity` |
| Undefined-name suppressions that exist only for the alias | 332 lines in 117 files (`# noqa: F821`, `# type: ignore[name-defined]`, and 13 file-level `# ruff: noqa: F821`) | `grep -rn 'noqa: F821\|type: ignore\[name-defined\]'`; the scan reports the same 332 |
| Extra fields declared on value classes | 187 classes: `int` 45, `str` 31, `bool` 6, `Opaque` 2, `ClassVar[Any]` 1, `list[str]` 1 | AST scan of class bodies whose base name ends in `EnumEntity`/`StateEntity` |
| The one mutable property in the corpus | `OrderStateEntity.labels: list[str]` — a **state** type, in `tests/action_machine/domain/test_lifecycle_current_status.py` | the same scan |
| The one non-JSON property in the corpus | `value: Opaque` — a **state** type, `examples/step_22_lifecycle/19_non_json_field.py` and `tests/.../graph_host/test_lifecycle_graph_node.py` | the same scan |
| Dictionary example series | 25 scripts and 25 notebooks under `examples/step_20_dictionaries/` | directory listing |
| Card checks that already exist | `tests/test_list_entities_payload_dictionary.py`, `client/scripts/check-erd-dictionary-values.ts` (renders SVG through `@hpcc-js/wasm-graphviz`) | file inspection |
| Pydantic | 2.12.5; `GetJsonSchemaHandler` publishes `mode` | `.venv/bin/python -c "import pydantic; print(pydantic.VERSION)"` |

The last three rows matter more than they look. The only mutable property and the only non-JSON property in the whole corpus sit on **state** types, and the state suite states that a status may carry "data that need not be hashable". A rule that refuses mutable properties for both kinds would break two existing contracts that #244 does not ask to change.

## D1 — Remove the alias, keep the conversion

**Decision**: delete `_DeclaredValuesNamespace`, `DeclaredValuesMeta`, the `metaclass=` argument on both kinds and the `pydantic._internal._model_construction` import. `value(**kwargs) -> ValueSpec` becomes the authored form and is exported from `aoa.action_machine.domain`. `_DeclaredValues.__pydantic_init_subclass__` keeps converting `ValueSpec` placeholders into instances, computing `members`, `codes()`, `by_code()`, `entity_type`, the duplicate refusal and the per-kind switches, exactly as it does now.

**Rationale**: the conversion never depended on the namespace. It reads `cls.__dict__` for `ValueSpec` values and replaces them with `setattr` after Pydantic has built the model — a step that works with Pydantic's ordinary metaclass. Both kind markers already declare `ignored_types=(ValueSpec,)` in `model_config`, so a placeholder in the class body is not read as a field. The namespace only made `ClassName(...)` resolve; nothing else used it.

**Prototype**: with the alias in place, a class body that writes `EUR = value(...)` already produces a working catalogue today — `test_declared_values.py::test_the_declaration_factory_is_plain` shows the factory returning a `ValueSpec` and `__pydantic_init_subclass__` converting it. The removal is therefore subtraction, not new machinery.

**Alternatives rejected**: keeping the metaclass for a deprecation window (the issue forbids a compatibility path, and two forms would need two documented declaration stories); converting placeholders in `__init_subclass__` instead (Pydantic's model fields do not exist yet at that point); a separate Python `Enum` (explicitly out of scope).

## D2 — `value()` is typed `-> Any` for the checker

**Decision**: `def value(**kwargs: Any) -> Any:` — it returns a `ValueSpec` at runtime, and the annotation is `Any`.

**Rationale**: the declared name is written before the class exists, so no generic parameter can express "an instance of the class being defined". Today the class-name call is type-correct because `CurrencyEnumEntity(...)` is an instance; `EUR = value(...)` would otherwise be seen by `mypy --strict` as a `ValueSpec` attribute, and every `currency=CurrencyEnumEntity.EUR` would fail across 373 declarations and dozens of tests. `Any` is the only annotation that keeps the corpus type-checked without a `# type: ignore` per declaration — and it is honest: the object at that point is genuinely untyped.

**Alternatives rejected**: generic `value[T]()` (the class does not exist yet, so `T` cannot be named); `cast` at every declaration (373 casts, and `cast` would need the class anyway); keeping the class-name form (D1).

## D3 — The immutability rule binds the dictionary kind only

**Decision**: the supported-type rule of D4 lives in `_DeclaredValues` behind a per-kind switch (`__declared_values_immutable__`, default `False`, `True` on `BaseEnumEntity`). Statuses keep their present freedom.

**Rationale**: three facts, not a preference. `to_reference()` — the thing a consumer receives and can mutate — exists only on `BaseEnumEntity`; #244's work item is titled "Immutability of shared **dictionary** values"; and the corpus's only mutable property (`list[str]`) and only non-JSON property (`Opaque`) are statuses whose behaviour the same issue orders preserved, one of them asserted as a deliberate scenario. Binding both kinds would either break those or grow an exception list inside the rule.

**Alternatives rejected**: binding both kinds and rewriting `test_lifecycle_current_status.py` plus `19_non_json_field.py` (contradicts FR-031 and changes a documented lifecycle scenario); binding neither (leaves the reproduced defect); freezing on export while accepting lists (D5 and FR-009 rule it out: the declared instance itself would stay mutable).

## D4 — The supported property types, and the recursive refusal

**Decision**: a dictionary value's extra fields are limited to immutable leaves — `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `time`, `UUID`, `Enum` subclasses, `Literal[...]` — plus `tuple[...]` of supported values and `Optional[...]`/`X | None` of a supported value. `list`, `dict`, `set`, `frozenset`, nested models, arbitrary classes and a bare `Any` are refused at class creation with a message naming the class, the field and the refused type. The check walks `cls.model_fields` annotations with `typing.get_origin`/`get_args`, recursively, and runs in `__pydantic_init_subclass__` when the kind's switch is on.

**Rationale**: with no mutable container and no nested model, every exported value is immutable by construction — no copy is needed anywhere, which is the strongest form of FR-009 and removes the "shallow copy" trap the issue names. `frozenset` is refused despite being immutable because `model_dump(mode="json")` cannot represent it, so accepting it would move an error from declaration to export. `Any` is refused because it cannot be classified, and a value that cannot be classified cannot be promised immutable.

**Evidence it is affordable**: 0 dictionaries in `packages/` and `examples/` declare a `list`, `dict` or nested model property (AST scan above); the 45 `int`, 31 `str` and 6 `bool` fields are all inside the supported set. The refusal is therefore a guarantee for the future, not a migration of the present.

**Alternatives rejected**: freeze at class creation (the instance would present `tuple` where `list` is declared — a declared/runtime mismatch); deep copy on export (leaves `ITEM.labels.append` open, the issue's second path); accept anything and document it (contradicts FR-010).

## D5 — The reference form is the value's JSON-mode export

**Decision**: `to_reference()` becomes

```python
dumped = self.model_dump(mode="json")
return {
    "code": dumped["code"],
    "display_name": dumped["display_name"],
    "properties": {k: v for k, v in dumped.items() if k not in {"code", "display_name"}},
}
```

and the core schema's `plain_serializer_function_ser_schema` keeps calling it.

**Rationale**: `model_dump(mode="json")` is the one call that applies field serializers *and* converts standard types. Prototyped on the baseline's Pydantic:

```
python: {'code': 'item', 'display_name': 'Item', 'since': '02/01/2020'}
json  : {'code': 'item', 'display_name': 'Item', 'since': '02/01/2020'}
```

The custom serializer runs in both modes (its default `when_used` is `always`), and with no serializer a `date` becomes its ISO string in JSON mode — so the graph, the model's JSON output and the reference form agree, and `json.dumps(to_reference())` stops raising.

**Recursion**: the serializer calls `to_reference`, which calls `model_dump`, which does not re-enter the plain serializer (that is a *serialization* hook on the model's core schema, not a validation one). A dictionary-typed field inside a value cannot exist (D4 refuses nested models), so no second hop exists. A test asserts a single call and a JSON-serializable result.

**Alternatives rejected**: two forms — native and JSON (two shapes to document, and a consumer can still receive a non-serializable leaf); converting at the call sites (the defect returns with the next caller); `model_dump()` in Python mode plus a converter (**loses** serializers, which is the reproduced defect).

**Consequence to document**: `model_dump()` in Python mode may still return a `date`, and the pages say so; the reference form never does. `examples/step_20_dictionaries/03_serialization.py` asserts `model_dump()["currency"] == to_reference()` — true for its `str` fields, and reworded to name the mode explicitly.

## D6 — A mode-aware JSON schema, with serialization-aware per-property types

**Decision**: `BaseEnumEntity.__get_pydantic_json_schema__` branches on `handler.mode` (published by `GetJsonSchemaHandler` in Pydantic 2.12.5, verified at runtime):

- **validation**: `{"type": "object", "additionalProperties": false, "required": ["code"], ...}` with `code` a non-blank string, `display_name` a string, `properties` an open object — the shape the runtime accepts today.
- **serialization**: `required: ["code", "display_name", "properties"]`, and `properties` an object that declares every extra field by name with its emitted JSON type, `additionalProperties: false`.

The per-property schemas are **not** `TypeAdapter(field.annotation).json_schema(mode=...)`: prototyped, that ignores a `@field_serializer` and still reports `{"format": "date", "type": "string"}` for a field whose serializer returns `%d/%m/%Y`. The decision is to generate the class's own serialization schema from a metadata-stripped copy of its core schema and lift `properties` out of it:

```python
copy = dict(schema)
copy.pop("metadata", None)          # drop this hook, or it recurses
inner = GenerateJsonSchema().generate(copy, mode="serialization")
```

Prototyped: the serialized property comes out as `{"type": "string"}` — no stale `format` — while the validation branch stays open. `title` and `description` are stripped from the lifted properties, because the outer object is not a model schema and those keys would drift with Pydantic's labels.

**Rationale**: the issue requires the output schema to describe what is emitted, and a serializer can change a type; only the class-level serialization schema knows that. The metadata strip is what breaks the recursion: the hook is registered in `metadata.pydantic_js_functions`, so generating without it calls the plain generator once.

**Safety of the strip**: with D4's supported set there are no nested models, hence no `$defs` to lose. A test asserts that a serialization schema never contains `$defs` for a dictionary value; a second asserts the hook is entered once per mode and does not recurse.

**Alternatives rejected**: one schema for both modes (the reproduced defect); `TypeAdapter` per field (loses serializers, prototyped); a hand-written map from Python type to JSON schema (a second source of truth that drifts from Pydantic's own conversions).

## D7 — The input side stays open where the runtime is blind

**Decision**: validation mode accepts `{"code": "eur"}`, `{"code": "eur", "display_name": "Euro"}` and a full reference; `properties` is `{"type": "object"}` with no member constraints. Serialization mode types every member. The asymmetry is documented in the contract as intentional.

**Rationale**: runtime validation resolves by `code` and ignores the rest (FR-019), so an input schema that constrained `properties` would reject payloads the runtime accepts — the mirror image of the defect being fixed. The output side has no such freedom: it describes exactly what is emitted.

**Alternatives rejected**: symmetric schemas (either over-constrains input or under-describes output); a `discriminator`/`oneOf` between code-only and full (more machinery than two objects, and the runtime does not distinguish them).

## D8 — The card carrier is preserved; only the text form is completed

**Decision**: `ListEntitiesAction` keeps building `[{name, value}]` with `json.dumps(item, ensure_ascii=False)` for a non-string item; the payload schema is unchanged; `buildDotSource.ts` keeps escaping and rendering. What changes is upstream: a tuple now arrives as a JSON array instead of never arriving at all, and a serializer's string arrives instead of the raw object.

**Rationale**: #243 already merged the carrier and the strict schema; #244 asks to verify it after the serialization fixes, not to replace it. The existing checks (`test_list_entities_payload_dictionary.py`, `check-erd-dictionary-values.ts`) cover the escaping and the SVG render, and are reused.

**Consequence**: the `value` member is a string in every case — a string property as its text, a number/boolean/array as `json.dumps` of it (`42`, `true`, `["a", "b"]`). Deterministic because `json.dumps` is called with fixed arguments and `ensure_ascii=False`.

**Alternatives rejected**: the `properties_json` string carrier from #242 (superseded by #243); typing `value` as a union in the payload (the strict `JsonSchemaValue` shape and the renderer both expect text).

## D9 — The server owns the group label

**Decision**: the payload's `label` stays `field (by classifier_or_dictionary)` and is what the client renders; the client stops appending ` (${dictionary_label})`; `dictionary_label` leaves the group's payload shape, its JSON schema and `ErdGroup`. The classification field stays in the payload, because it is a fact other than the label.

**Rationale**: one owner, and it is the layer that already composes `label` for entities and relations in the same payload — the client's contract is "render the label you are given". The duplication exists because the client composes presentation text a second time from a field it also receives.

**Tests to update**: `test_list_entities_specialization_contract.py` asserts the exact key set of a group (it loses `dictionary_label`); `test_entity_specialization_erd.py` lists the same key; `ErdGraphvizCanvas/README.md` line 56 documents the old composition.

**Alternatives rejected**: the client composing from facts (wider change, and it inverts the payload's existing convention); dropping only the client's append while keeping `dictionary_label` in the shape (leaves an unused field documented as meaningful).

## D10 — Migration mechanics

**Decision**: one throwaway codemod, run before commit 1 is prepared, with three rules per file: (1) replace `= <Owner>Entity(` with `= value(` only where the assigned name is uppercase and the class body's owner matches the enclosing class; (2) add `value` to the module's existing `from aoa.action_machine.domain import (...)` list, or to a new import if the module imports the marker from a deeper path; (3) strip `# noqa: F821` / `# type: ignore[name-defined]` from the migrated lines. Notebooks are rewritten by the same rules over code cells only, then executed in the documentation phase. A scan (`evidence/scan_value_declarations.py`) must report 0 class-name declarations and 0 alias-only suppressions afterwards, per area.

**Rationale**: 373 declarations across 116 files cannot be hand-edited without drift, and `test_declared_values.py` must be rewritten by hand because it asserts the alias itself (`test_an_unknown_name_in_the_class_body_still_raises` becomes meaningless and is deleted, not adapted). The demo is included (spec, Clarifications) because its modules are imported by the demo's tests and the check run runs them.

**Guard**: the codemod refuses to edit a file whose migrated count does not match the declaration count it found, so a partial rewrite cannot pass silently; the scan runs before and after.

**Alternatives rejected**: hand migration (unreviewable); a compatibility alias (forbidden); migrating only the framework (breaks the demo's pytest step).

## D11 — The Russian drafts

**Decision**: the documentation pages of this change get no `*.ru_draft.md`; the English pages are updated in place. The planning artifacts keep their Russian twin — `tasks.ru_draft.md` beside `tasks.md` — because `.gitignore` keeps `*_draft.md` out of a commit and the maintainer reads the list in Russian.

**Rationale**: #244 states it twice — "Do not create Russian draft documentation" and "Do not create Russian drafts" — and that sentence is about the pages under `docs/`, which a reader of the manual sees. The task list is a working artifact the maintainer reads while directing the work; #241 kept `tasks.ru_draft.md` the same way, and it never entered a commit.

## Open questions

None. Every `NEEDS CLARIFICATION` of the specification was resolved before planning; the five decisions recorded in `spec.md` under "Session 2026-10-23 — clarifications" are carried into D1–D11 without reopening.
