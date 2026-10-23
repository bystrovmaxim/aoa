# Implementation Plan: an explicit `value(...)`, a protected value, one reference form, one label

**Branch**: `feature/issue-244-simplify-value-declarations` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-value-declaration-consistency/spec.md`

## Summary

The declaration of a shared value is hidden in the class's own name: a metaclass substitutes a factory for a name that does not exist yet, so `EUR = CurrencyEnumEntity(...)` builds a placeholder. The same machinery leaves four defects measured on `e791ad28`: a declared value's nested data is mutable through `to_reference()`, a `@field_serializer` is bypassed because the reference is read with `getattr`, the published JSON schema requires three members while the runtime accepts one, and the specialization group label is composed twice — once in SQL, once in the client.

The change has six work items and nine phases:

1. **The declaration becomes explicit.** `value(...)` is exported from `aoa.action_machine.domain`, the namespace, the metaclass and the Pydantic-internal dependency are deleted, and all 373 declarations across 116 files — framework, tests, examples, notebooks and the demo — migrate in the same commit, because the alias cannot leave half-way.
2. **The value is protected.** A dictionary value's extra fields are limited to immutable types, checked recursively at class creation; the state kind keeps its present freedom.
3. **The reference form is the JSON export.** `to_reference()` becomes `model_dump(mode="json")` split into `code`, `display_name` and `properties`, so serializers run and every leaf is JSON.
4. **The schemas split.** A mode-aware hook makes the input schema accept a code-only reference and the output schema describe each emitted property by its serialized type.
5. **The card is verified end to end.** The carrier #243 merged is preserved; the full path is proven and the missing cases (array property, empty property list, an escaped value) are added.
6. **The label gets one owner.** The server composes it, the client stops appending, `dictionary_label` leaves the group shape.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`); Pydantic 2.12.5 supplies the core-schema and JSON-schema hooks (`GetJsonSchemaHandler.mode` exists in this version, verified at runtime); TypeScript for the Maxitor client.

**Primary Dependencies**: no new dependency. The framework uses Pydantic's public core-schema API and `pydantic.json_schema.GenerateJsonSchema`; `jsonschema` already validates payloads; `@hpcc-js/wasm-graphviz` already renders the SVG in the client check.

**Storage**: none. The graph's reference shape does not change, so a saved graph keeps working; no migration and no rebuild.

**Testing**: `pytest` per package; `mypy --strict` across eight packages; ruff, pylint; the client build; the two client check scripts; and the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial per `AGENTS.md`: reintroduce each corrected defect in isolation, confirm its test fails and no other, restore.

**Target Platform**: `aoa-action-machine` (declaration machinery, core schema, JSON schema), `aoa-maxitor` (payload action, payload schema, client renderer), `examples/step_20_dictionaries` and the pages that carry the declaration form.

**Project Type**: library monorepo; the change is a framework change plus a corpus migration plus one viewer path.

**Performance Goals**: no runtime cost. The property-type check runs once per dictionary class at import; `model_dump(mode="json")` replaces a `getattr` loop of the same order; the schema generation is unchanged in count.

**Constraints**: no compatibility form for the removed alias (FR-003); `value()` annotated `-> Any`, because no generic can name a class that does not exist yet and 373 declarations cannot carry a `# type: ignore`; one commit per phase, each leaving the tree green — which forces the alias removal and the whole corpus migration into one commit; every new symbol keeps its module header (III), AI-CORE block (IV) and one-line docstrings (V); English throughout (II); nothing is committed without instruction (I).

**Scale/Scope**: 373 class-name declarations in 116 files (270 in 91 outside the demo, 103 in 25 inside); 332 alias-only suppressions in 117 files; 25 dictionary example scripts and 25 notebooks; 2 kind markers, 1 declaration module, 1 core-schema hook, 1 JSON-schema hook, 1 Maxitor action SQL, 1 payload schema, 2 client files, 1 client check added, 7 documentation pages, 2 earlier planning pages reconciled, 4 changelogs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Nine phases; each becomes a commit only on instruction. The branch `feature/issue-244-simplify-value-declarations` exists on the maintainer's word; nothing is pushed. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | New code, refusal messages, tests, pages and the changelog are English. The questions of the clarification session were put in Russian for the maintainer, and their answers were recorded in the spec in English. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | `declared_values.py` and `enum_entity.py` keep their headers and are updated where the machinery leaves; new test modules carry the header form the package already uses. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `BaseEnumEntity`'s block is updated for the supported-type rule and the JSON-only reference; `value()` (module-level, public) gains a block; `to_reference()` keeps its role and gains the JSON-mode contract; `ListEntitiesAction`'s block is unchanged. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol: the type walker, the refusal, the two schema branches, the lifted-property helper, each new test. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 7, 8 and 9 are those three, in that order, and no earlier phase absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | Phase 8 adds the four cases this feature introduces — the refused mutable property, a serializer's text, the two schema modes, the single label — as scripts and notebooks beside the existing `step_20_dictionaries` series, and executes the whole series (25 scripts, 25 notebooks) while writing. No new series is created. |

**Violations requiring justification**: none. Complexity Tracking records the public-API break, the refusal-over-freezing choice, and the metadata-stripped schema generation as deliberate costs.

**Re-checked after Phase 1 design**: unchanged. The design deletes more machinery than it adds: one module loses two classes and an import, one class gains one classmethod, one hook gains a branch, one SQL line loses a concatenation, one client line loses an append, and one payload schema loses a property.

## Project Structure

### Documentation (this feature)

```text
specs/016-value-declaration-consistency/
├── plan.md                          # this file
├── spec.md                          # the specification
├── research.md                      # Phase 0: D1–D11, prototypes and measured counts
├── data-model.md                    # Phase 1: declaration, value, reference, two schemas, card, label
├── quickstart.md                    # Phase 1: ten runnable proofs
├── contracts/
│   ├── declared-value.md            # the declaration, the type set, the reference form, the schemas, the refusals
│   └── dictionary-card.md           # graph reference → payload → card, and the label
├── evidence/
│   ├── scan_value_declarations.py   # counts per area, before and after
│   ├── migrate_value_declarations.py # the codemod, with its count guard
│   ├── reproduce_defects.py         # the four baseline defects, printed
│   ├── baseline.before.txt          # the branch, the tool versions, the scan table, the dry run
│   ├── defects.before.txt           # the four defects, printed on the baseline
│   ├── baseline.after.txt           # the same scan after the migration
│   └── closing-check-run.md         # the run to zero and every adversarial break
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/domain/
│   ├── declared_values.py           # the namespace and metaclass DELETED; value() exported; the type check
│   ├── enum_entity.py               # no metaclass; to_reference = JSON dump; mode-aware JSON schema
│   ├── state_entity.py              # no metaclass; catalogue behaviour untouched
│   └── __init__.py                  # exports value
└── tests/action_machine/
    ├── domain/test_declared_values.py        # rewritten without the alias
    ├── domain/test_dictionary_core_schema.py # JSON-mode reference, serializer
    ├── domain/test_dictionary_scope.py       # reference form unchanged for strings
    ├── domain/test_dictionary_property_types.py   # NEW — accepted set, recursive refusals, status freedom
    ├── domain/test_dictionary_json_schema.py      # NEW — two modes, serializer type, no $defs, no recursion
    ├── domain/test_lifecycle_current_status.py    # untouched; proves the state kind keeps its freedom
    └── graph/test_dictionary_reference_json.py    # NEW — the graph document JSON-parsed

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action.py         # group SQL: label only, no dictionary_label
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py  # group shape loses dictionary_label
├── client/src/lib/buildDotSource.ts                # no second append; ErdGroup loses dictionary_label
├── client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/README.md  # the label contract
├── client/scripts/check-erd-dictionary-values.ts   # extended: array property, empty list, escaping
├── client/scripts/check-erd-group-label.ts         # NEW — payload through the renderer, one name
└── tests/
    ├── test_list_entities_payload_dictionary.py    # the full path, the text forms
    ├── test_list_entities_specialization_contract.py  # the group key set, the label text
    └── test_entity_specialization_erd.py              # the same key set

examples/step_20_dictionaries/                     # 25 scripts + 25 notebooks migrated; 4 cases added
packages/aoa-demo/                                  # 103 declarations in 25 files, mechanical only
docs/                                               # step-20-dictionaries, step-21, step-22, the how-to,
                                                    # architectural-constitution, the Maxitor component README
specs/015-closed-dictionary-variants/               # contract and plan reconciled with what was resolved
docs/CHANGELOG.md, packages/*/CHANGELOG.md
```

**Structure Decision**: the machinery stays in `aoa-action-machine/domain` — one module loses its two classes, one class gains the type check and the JSON-mode reference, one hook gains a branch. Maxitor changes one SQL line, one schema member and one client line, plus a check that drives a payload through the renderer. The corpus migrates in place; no file moves.

## Phases

Each phase is one commit, on instruction, and leaves the tree green.

| # | Phase | Outcome | Green because |
| --- | --- | --- | --- |
| 1 | **The explicit declaration, and the corpus on it** | `value(**kwargs) -> Any` and `ValueSpec` are the only declaration machinery; `_DeclaredValuesNamespace`, `DeclaredValuesMeta`, both `metaclass=` arguments and the `ModelMetaclass` import are deleted; `value` is exported from `aoa.action_machine.domain`; the codemod rewrites 373 declarations in 116 files, 25 notebooks and 332 suppressions; `test_declared_values.py` is rewritten by hand (the alias test is deleted, not adapted); `evidence/scan_value_declarations.py` records 373/332 before and 0/0 after | The alias and its last user leave in one commit: no file keeps the old form, so no import can fail. The catalogue, the duplicate refusal, the empty-dictionary refusal and the state kind's inheritance are unchanged, and their existing tests prove it. |
| 2 | **A dictionary value carries no mutable data** | The per-kind switch `__declared_values_immutable__` (off on the state kind, on for `BaseEnumEntity`); the recursive walk of `model_fields` over the supported set; the refusal message naming the class, the field and the type; `test_dictionary_property_types.py` with one accepted and one refused case per type and the nested cases; the state suite untouched and green | No dictionary in the corpus declares a refused type (measured: none), so nothing migrates; the only `list[str]` and the only `Opaque` property are statuses, whose switch is off. |
| 3 | **The reference form is the JSON export** | `to_reference()` = `model_dump(mode="json")` split; the core schema's plain serializer keeps calling it; a serializer's text and a `date`'s ISO string reach the reference; `json.dumps` never raises; `test_dictionary_core_schema.py` and `test_dictionary_scope.py` updated; `test_dictionary_reference_json.py` proves the actual graph document | Every existing dictionary in `examples/` and the tests carries `str` fields only, so the emitted shape is byte-identical for them; the changed assertions are the ones that name the mode. |
| 4 | **Two schema contracts** | The mode-aware `__get_pydantic_json_schema__`; validation accepts `{"code"}` and a full reference with open `properties`; serialization requires `code`, `display_name`, `properties` and types each property from a metadata-stripped serialization generation; `test_dictionary_json_schema.py` covers both modes, a serializer's type, the absence of `$defs` and the single hook entry | The graph schema and the Maxitor payload schema describe other documents and do not change; runtime validation is untouched, and the existing refusal tests still pass. |
| 5 | **The card, proven after the fixes** | The full path — declared value → graph → DuckDB → `ListEntitiesAction` → validated payload → DOT → SVG — has a test per value shape: two properties, a property with `<`, `>`, `&`, a value with none, a model with no dictionaries, and an array property; the client check renders the SVG; the payload test fails when a member is dropped between graph and card | The carrier is #243's and is not rewritten; only coverage is added, and the payload schema still accepts what the action emits. |
| 6 | **One owner for the group label** | The SQL composes `field (by …)` and the client renders it; the second append is deleted; `dictionary_label` leaves the payload schema, the group dict and `ErdGroup`; `check-erd-group-label.ts` feeds the server payload through `buildDotSource`; the two payload tests assert the new key set; the component README states the single-owner rule | The label text for every existing axis is unchanged in value (it loses only the duplicate), and the key-set assertions are updated in the same commit. |
| 7 | **The check run (VI.1)** | `bash scripts/run_checks_with_log.sh` taken to zero; the adversarial breaks recorded with their commands and results | It is the check |
| 8 | **The documentation (VI.2, VI.4–VI.6)** | `step-20-dictionaries` (the declaration, the type set, the reference form, the two schemas), `step-21` and `step-22` (their declaration examples), the how-to page's messages, `architectural-constitution`'s example, the Maxitor tutorial and the component README, and the reconciliation of `specs/015-.../contracts/dictionary-declaration.md` and the stale ERD risk in `specs/015-.../plan.md`; the four new cases as scripts and notebooks; all 25 dictionary scripts and their notebooks executed; no Russian draft for the pages, while the task list keeps its `tasks.ru_draft.md` | Docs and examples only; every example is run while written. |
| 9 | **The changelog (VI.3)** | One article in `docs/CHANGELOG.md`; `[Unreleased]` entries in `packages/aoa-action-machine`, `packages/aoa-maxitor`, `packages/aoa-demo` | Text only |

The closing tail is **three commits**, one per task and in the order of constitution VI: T044 is the check run, T045 is the documentation with the quickstart proof (T047), T046 is the changelog. The table lists them under one heading only because they share the same dependency — every story is done.

Phase 5 is a verification phase in substance: #243 already merged the carrier, so its work is adding the missing value shapes and the drop-between-layers adversarial case, not new plumbing. Its documentation half belongs to phase 8, because VI.2 puts documentation after the code is settled — including the reconciliation of the earlier planning pages, which describes what was resolved rather than changing behaviour.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The alias removal leaves one declaration behind, and the import fails only in a path the tests do not load | The codemod refuses a file whose migrated count differs from the count it found; `scan_value_declarations.py` reports 0 before the commit is prepared; the demo is migrated too, so its pytest step imports every module |
| `mypy --strict` sees `ValueSpec` where an instance is expected | `value()` is annotated `-> Any`; a test module declares a value and passes it to a dictionary-typed field, so the annotation is exercised by the checker |
| The JSON-schema hook recurses into itself | The serialization branch generates from a copy with `metadata` removed; a test asserts exactly one hook entry per mode and that generation terminates |
| The lifted property schemas carry `$defs` or a stale `format` | The supported set has no nested models; a test asserts no `$defs` and that a serialized `date` property is a plain `string` |
| The type check breaks the state kind, or a status the lifecycle suite depends on | The switch is per kind and is off for `BaseStateEntity`; `test_lifecycle_current_status.py` and `19_non_json_field.py` are not edited and stay green |
| A dictionary in the demo or an example declares a type the rule now refuses | Measured: none does; the scan runs in phase 1 and again before phase 2's commit, and a name would stop the commit rather than surprise a reader |
| `to_reference()` in JSON mode changes an assertion that compared it with `model_dump()` | The assertion is about `str` fields; it is reworded to name the mode, and a new test covers a serializer and a `date` where the two modes differ |
| The output schema becomes brittle against a Pydantic upgrade | The tests assert the contract (required members, the property's type, no `$defs`), not the whole generated document; `title` and `description` are stripped |
| Removing `dictionary_label` breaks another reader of the group shape | The grep is closed: the only readers are the client type, its append, two payload tests and the component README, and all are updated in the same commit |
| The client check passes on DOT text but the SVG loses a character | The check renders through `@hpcc-js/wasm-graphviz` and asserts inside the SVG, as the existing dictionary check already does |
| The codemod corrupts a notebook's JSON | Only code-cell sources are rewritten, re-serialized with the same indentation, and the load is aborted on failure; the notebooks are executed in phase 8 |
| The check run's two accepted remarks are joined by a new one | Phase 7 fixes every remark except the two named in the constitution |

## Complexity Tracking

| Deliberate cost | Why needed | Simpler alternatives rejected because |
| --- | --- | --- |
| A public API break with no deprecation window | Two declaration forms would need two documented stories and two test surfaces, and the alias is the thing this feature exists to remove | Keeping the alias for a deprecation period (forbidden by FR-003 and by the issue); a warning that still lets the hidden substitution run (two mechanisms, one documented as unsupported) |
| Refusing mutable and nested property types instead of freezing them | With no mutable container in a value, the exported form is immutable by construction and no copy can be forgotten; the issue names both paths — the export and the attribute — and freezing only one leaves the other | Freezing at class creation (the instance would present `tuple` where `list` is declared); a deep copy on export (leaves `ITEM.labels.append` open); a per-type converter (a second serialization path) |
| Generating the output schema from a metadata-stripped copy of the class's core schema | The schema must describe the serializer's output type, which only the class-level serialization generation knows; a per-field adapter reports the declared Python type instead | `TypeAdapter` per field (prototyped: loses the serializer); a hand-written type map (drifts from Pydantic); one schema for both modes (the reproduced defect) |
| A codemod for 373 declarations, 25 notebooks and 332 suppressions | The rule that removes the alias and the migration must land together, and 116 files cannot be edited by hand without drift | Hand migration (unreviewable diff); a compatibility shim (the second form FR-003 forbids); migrating in two commits (the first leaves the tree red) |

## Re-checked after Phase 1 design

Unchanged in cost. The design removes a metaclass, a namespace class and a Pydantic-internal import; adds one classmethod, one hook branch, one helper, one export, one check script and four tests. It adds no dependency, no storage change, no route, no graph shape change and no new example series.
