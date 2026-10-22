# Implementation Plan: A closed dictionary declares its variants, and specialization takes its codes from it

**Branch**: `feature/issue-241-closed-dictionary-variants` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/015-closed-dictionary-variants/spec.md`

## Summary

An entity kind's catalogue already exists: since #237 a state type declares its statuses in its own body and exposes `members`, `codes()` and `by_code()`. The dictionary kind has none of that and is not closed at all — `code` is a field the model writes, a value is an instance nobody declared, and a field that references a dictionary is a plain `str` that accepts `"bootleg"`. A specialization meanwhile states its code set three times: a `Literal` on the head, a `Literal` on every extension, and nothing anywhere that could reject a value arriving from data.

The change has four blocks, each its own commit:

1. **The dictionary kind declares its values.** The state kind's machinery moves into a kind-neutral mixin and metaclass; `BaseEnumEntity` gains `code`, `display_name`, the declaration in the class body, the catalogue, the duplicate refusal, and the refusal of an empty concrete dictionary. Values are not inherited, unlike the state kind's catalogue.
2. **A dictionary is a type.** A field typed by the dictionary accepts a declared code or the declared instance, refuses an unknown code and a constructed copy, serializes the value whole with its extra fields under `properties`, and reads by the code. The graph carries the values on the dictionary node and marks a referencing field.
3. **Specialization borrows the set.** `Specialization[T, D]` takes the dictionary as a type argument; the head carries neither a classifier field nor a head-side `Classifier`; each extension names its field and the declared value it is; the container refuses a bare code and a value that disagrees with the hydrated row; the build refuses a `Literal`, a value with no alternative, an alternative with no declared value, and a copy; the axis edge publishes the dictionary.
4. **The corpus and the viewer follow.** The demo's 25 currency fields reference a dictionary, the 110 axes of the examples and the framework's tests move onto the dictionary form, and Maxitor renders the card, the reference and the axis label from the graph alone.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`). Eight packages under `packages/`; 191 example scripts with 189 notebooks, of which 38 scripts and 38 notebooks are touched by the migration; the Maxitor TypeScript client and its Vite build are touched only by block 4.

**Primary Dependencies**: no new dependency. Pydantic v2 supplies the core-schema hooks (`__get_pydantic_core_schema__`, `__get_pydantic_json_schema__`), `__pydantic_init_subclass__`, and `model_config["ignored_types"]`; `jsonschema` already validates the interchange document; DuckDB backs Maxitor's graph store.

**Storage**: no schema change beyond the viewer's own tables. The Maxitor DuckDB store gains a `values_json` column on `entity` and a `reference_qualname` column on `entity_field`; the graph JSON is rebuilt rather than versioned.

**Testing**: `pytest` per package, `mypy --strict` across the eight packages, ruff, pylint, the client build, and the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial per `AGENTS.md`: break each refusal and each graph field one at a time, confirm the dedicated test fails and no other, restore.

**Target Platform**: the eight Python packages, the demo model, the examples and their notebooks, and the Maxitor client. The graph document is the contract between the engine and the viewer.

**Project Type**: library monorepo — `aoa-action-machine` changes the framework; `aoa-demo`, `examples/` and the framework's tests migrate; `aoa-maxitor` renders the new properties; `docs/` and the changelogs follow.

**Performance Goals**: no runtime cost. The declaration, the catalogue and the refusals run once per class at import; the specialization checks run once per graph build in the pass that already exists; the client renders rows it already receives.

**Constraints**: no new dependency; the container is generic (`Specialization[T, D]`) and `variant` is typed by the dictionary, so `mypy --strict` checks every axis's second argument; every commit on the branch leaves the tree green, which forces the example and test migration into the same commit as the rule that refuses `Literal`; `mypy --strict` with no new `# type: ignore`; every new module keeps its principle-III header; new public symbols get AI-CORE blocks (IV) and one-line docstrings (V); English throughout (II); nothing is committed without the maintainer's instruction (I).

**Scale/Scope**: 25 currency fields in 22 demo files; 1 dictionary in the examples and the demo each; 110 axes to migrate — 48 in 38 example scripts (with 38 notebooks), 61 in 7 framework test modules, 1 in the demo — each losing its classifier field; 252 `Classifier(…, Literal[…])` declarations to rewrite — 142 in the examples and 107 in the tests by codemod, 3 in the demo by hand; 1 new framework module, 2 kind markers edited, 1 container made generic, 1 validator, 1 graph schema, 1 Maxitor resource, 1 Maxitor action with its schema, 2 client files and a component README; 1 evidence script with a before/after graph.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Nine phases; each becomes a commit only on instruction, and the branch already exists on the maintainer's word. The baseline phase ends with the numbers shown before any migration starts. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | New module, the two markers, the validator messages, the tests, the pages and the changelog are English; the Russian drafts stay beside their pages. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | `declared_values.py` is written with the full header; `state_entity.py`, `enum_entity.py`, `entity_specialization_validator.py`, `graph_json_schema.py` and the Maxitor resource keep or restore theirs as they are touched. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `BaseEnumEntity` and `BaseStateEntity` blocks are rewritten for the shared mechanism; the validator's new rule and `ListEntitiesAction` get their blocks updated; the internal mixin, metaclass, placeholder and factory carry one-line docstrings only. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol gets one: the mixin, the metaclass, `value()`, `ValueSpec`, `members`, `codes()`, `by_code()`, `entity_type`, `to_reference()`, each new rule, each new test. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 7, 8 and 9 are those three, in that order, and no earlier phase absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | The three cases — declaring a closed dictionary, referencing a value from a field, classifying an axis by a dictionary — are shown in pages that already exist (`step_20_entity/07_enumeration`, `step_20_entity/06_specialization`, `step_21_relations`); no new series is added. The 38 affected notebooks are rewritten by the same codemod as the scripts and executed in phase 8. |

**Violations requiring justification**: none. Complexity Tracking records the core-schema override and the codemod as deliberate costs.

**Re-checked after Phase 1 design**: unchanged. The design adds one internal module, one public method (`to_reference`), two graph properties, and one client renderer; it adds no dependency, no storage migration and no new example series.

## Project Structure

### Documentation (this feature)

```text
specs/015-closed-dictionary-variants/
├── plan.md                              # this file
├── spec.md                              # the specification
├── spec.ru_draft.md                     # its Russian draft (gitignored)
├── research.md                          # Phase 0: D1–D12, alternatives and measurements
├── data-model.md                        # Phase 1: dictionary, value, reference, axis, graph rows
├── quickstart.md                        # Phase 1: runnable proof of every case
├── contracts/
│   ├── dictionary-declaration.md        # the surface, fields, catalogue, refusals, field type, wire form
│   └── specialization-codes.md          # the head and extension forms, the four refusals, the edge
├── evidence/
│   ├── scan_dictionary_variants.py      # counts per area, axes, dictionaries, currency fields
│   ├── baseline.before.json             # the demo graph: enum nodes, values, reference fields, axis edges
│   ├── baseline.after.json
│   └── compare_baselines.py             # SC-006 evidence: identical or a named difference
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── domain/
│   │   ├── declared_values.py          # NEW — the mixin, the metaclass, ValueSpec, value(), the hook
│   │   ├── state_entity.py             # the catalogue moves to the mixin; behaviour preserved
│   │   ├── enum_entity.py              # code + display_name, values in the body, catalogue, core schema
│   │   ├── state_spec.py               # DELETED — folded into declared_values.py
│   │   ├── specialization_containers.py# Specialization[T, D] with a typed variant and the pairing check
│   │   └── spec_entity.py              # BaseSpecEntity exposes its declared value
│   ├── graph/
│   │   ├── nodes/entity_graph_node.py  # properties.values for the enum kind
│   │   ├── edges/entity_field_graph_edge.py # reference_qualname on a dictionary-typed field
│   │   ├── edges/entity_specialization_graph_edge.py # dictionary_qualname / dictionary_label
│   │   ├── validators/entity_specialization_validator.py # _validate_axis_vocabulary, vocabulary-first
│   │   └── graph_json_schema.py        # values (if/then on entity_kind), reference_qualname, edge props
│   └── intents/entity/…                # the specialization resolver reads the dictionary from the field
└── tests/action_machine/
    ├── domain/test_entity_kind.py      # the dictionary kind's declaration and catalogue
    ├── domain/test_dictionary_core_schema.py  # NEW — value/reference object/bare code/copy, serialization
    ├── domain/test_dictionary_scope.py # NEW — non-inheritance, empty concrete dictionary
    ├── domain/test_specialization_container.py # NEW — variant shapes, pairing check, None, serialization
    ├── domain/test_spec_entity.py      # NEW — declared_variant derived, refusal on a non-declared value
    └── graph/test_entity_specialization_vocabulary.py # NEW — the five build refusals, the shared dictionary, the edge

packages/aoa-demo/
├── src/aoa/demo/model/dictionaries/…   # NEW — DictionariesDomain, CurrencyEnumEntity
├── src/aoa/demo/model/**/entities/*.py # 25 currency fields in 22 files
└── src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py  # one dictionary axis

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py  # values_json, reference_qualname
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action.py     # payload fields
└── client/src/
    ├── lib/buildDotSource.ts           # ErdEntity.values, ErdField.reference_qualname
    ├── components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/…        # value rows, reference, label
    └── components/ui/…                 # the dictionary card's rows

examples/
├── step_20_entity/07_enumeration.py (+ .ipynb)   # the closed dictionary and a reference
├── step_20_entity/06_specialization.py (+ .ipynb)# the axis classified by a dictionary
└── step_21_relations/*.py (+ .ipynb)             # 37 scripts and their notebooks, migrated by codemod

docs/                                     # step-20, step-26, glossary, intents-and-invariants, how-to
packages/*/CHANGELOG.md, docs/CHANGELOG.md
```

**Structure Decision**: the framework work stays inside `aoa-action-machine/domain` (one new module, two markers, one marker deleted into the new module) and `aoa-action-machine/graph` (one validator, one schema, three edge/node files). The demo and the examples change only declarations plus the new dictionary module. Maxitor gains columns it reads and rows it draws; neither the route set nor the graph format's node types change.

## Phases

Each phase is one commit, on instruction, and leaves the tree green.

| # | Phase | Outcome | Green because |
| --- | --- | --- | --- |
| 1 | Setup and baseline | Branch confirmed; `scan_dictionary_variants.py` run; `baseline.before.json` records the demo's `enum` nodes (none), currency fields (25), axes and `Classifier` declarations; the numbers in the spec are current | No code changes |
| 2 | The dictionary kind declares its values | `declared_values.py` extracted from `state_entity.py`; `state_spec.py` deleted; `BaseEnumEntity` gains `code`, `display_name`, the body declaration, `members`, `codes()`, `by_code()`, `entity_type`; duplicates and an empty concrete dictionary refused; `examples/step_20_entity/07_enumeration.py` and its notebook rewritten; tests for the surface, the catalogue, the two refusals and the non-inheritance | The state kind keeps its own behaviour (its tests prove it); no other kind changes; no field is typed by a dictionary yet, so no graph changes |
| 3 | A dictionary is a field type | The core schema and its JSON-schema counterpart; `to_reference()`; `properties.values` on the enum node with the `if/then` schema; `reference_qualname` on a dictionary-typed field; tests for a value and a reference object accepted, a bare code, an unknown code and a copy refused, an absent value, serialization and the graph rows | The demo still declares `str` fields, which take the old path; the example dictionary gains one referencing field to prove the case; the viewer reads neither property yet and the loader ignores properties it does not know |
| 4 | Specialization borrows the set | `Specialization[T, D]` with a typed `variant` and the pairing check; `Classifier(field=…, variant=…)` on the extension and `declared_variant` derived on `BaseSpecEntity`; `_validate_axis_vocabulary` first in `_validate_axis`; the classifier-field rules deleted; `Literal` and a restated code set refused; `dictionary_qualname`/`dictionary_label` on the edge and no `classifier_field`; the codemod deletes 110 classifier fields, adds the type argument, rewrites 38 example scripts and 38 notebooks and 7 test modules; the negative examples that assert the old rule are rewritten | Every axis in `packages/` and `examples/` is on the container form in the same commit, so the new refusal has no lawful victim |
| 5 | The demo migrates | `DictionariesDomain` and `CurrencyEnumEntity`; 25 currency fields typed and `sales_core.py` defaulted to the declared value; the demo's axis moves onto a dictionary; the demo's tests updated; `baseline.after.json` recorded | The demo builds and its graph now carries a dictionary, values, references and the axis label; the before/after comparison is the evidence |
| 6 | Maxitor renders the dictionary | The card's value rows, the reference column, the axis container's label; the component README; client build | Nothing in the rendering names a dictionary, a kind or a value; the graph supplies all three |
| 7 | The check run (VI.1) | `bash scripts/run_checks_with_log.sh` taken to zero | It is the check |
| 8 | The documentation (VI.2, VI.4–VI.6) | `step-20` (the closed dictionary, the reference, the axis), `step-26` (the card, the reference, the label), the glossary, `intents-and-invariants`, the how-to page's messages, the demo's README entry; the affected example scripts and notebooks executed; `ru_draft` beside each page | Docs only; the touched examples and notebooks run while written |
| 9 | The changelog (VI.3) | One article in `docs/CHANGELOG.md`; `[Unreleased]` entries for `aoa-action-machine`, `aoa-demo` and `aoa-maxitor` | Text only |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The generic container's `variant` is not validated by the dictionary's core schema | A dedicated test per parametrization: a declared value and its reference object pass, a bare code and a copy are refused; `mypy --strict` checks the second type argument at the construction sites |
| The pairing check reads a class attribute that does not exist on a hand-built extension | `declared_variant` is derived in the Pydantic init hook for every `BaseSpecEntity` descendant; a test asserts it exists on an extension declared without any extra marker |
| The shared mixin is read as a kind base because it inherits `BaseEntity` | It does not inherit `BaseEntity`; a test asserts that a class inheriting the mixin and one marker has exactly one kind base, and that `_is_kind_base` stays false for the mixin |
| The state kind's behaviour changes while its machinery moves | The `014` test suite is the contract; the move is proven by running it before and after with no edit to its assertions |
| The dictionary's core schema accepts a constructed copy or refuses a legitimate code | Dedicated tests per input shape; a copy is refused by identity, a code by `by_code`, a mapping by its `code`; an unknown code's message names the declared set |
| A field typed by an intermediate dictionary (empty catalogue) resolves nothing | The build refuses a field whose type has no values, with a message naming the class and the type; recorded in the contract |
| `Optional[Dictionary]` and `Annotated[...]` annotations bypass the detection | The detection unwraps `Optional`/`Annotated` once, with a test per shape; the same unwrapping serves the classifier field's dictionary lookup |
| The graph's `values` is optional and an `enum` node silently loses them | The schema requires `values` when `entity_kind` is `enum`; a test validates a payload without them and expects the failure |
| The codemod generates a dictionary whose codes differ from the axis's `Literal` set | The generated class is built from the same `Literal` arguments; `compare_baselines.py` compares the pre/post axis codes, and the sweep test refuses a mismatch |
| The codemod corrupts a notebook's JSON | The notebook rewrite edits code-cell sources only, re-serialises with the same indentation, and the diff is reviewed per file; a failed load aborts the codemod |
| A migrated example loses its scenario | Each example keeps its file name and prose; the negative examples that assert the replaced rule are the only ones rewritten by hand, and the plan lists them |
| Maxitor draws a value row as a node | The card renderer reads `values` only; a client test asserts that no entity row is produced for a value |
| The axis label needs the dictionary at render time and the edge lacks it | The edge carries `dictionary_qualname` and `dictionary_label`; the payload test asserts both |
| The check run's two accepted remarks are joined by a new one | Phase 7 fixes every remark except the two named in the constitution |

## Complexity Tracking

| Deliberate cost | Why needed | Simpler alternatives rejected because |
| --- | --- | --- |
| A Pydantic core-schema override on the dictionary type | The field must accept a code from JSON and the declared instance from code, refuse a copy, and serialize the value whole — three behaviours a plain model schema does not give | A per-field validator misses every new field and the graph; a `CodeOf` marker repeats what the type already is; accepting only instances pushes resolution into every adapter |
| Extracting the state kind's machinery into a mixin and a metaclass | The state kind's mechanism is the one the specification requires for the dictionary; copying it makes two grammars | Copying into `enum_entity.py` (drift); a shared `BaseEntity` ancestor (read as a seventh kind base, refused by #210) |
| The codemod over scripts and notebooks | 249 declarations across 45 files and 38 notebooks cannot be migrated by hand without drift, and the rule that refuses `Literal` makes the migration atomic with the engine change | Hand migration (unreviewable diff, silent drift); a compatibility mode accepting `Literal` (the second grammar the specification forbids) |
| The dictionary as a type argument of the container, and no classifier field | The classifier field and the container's `variant` were two statements of one fact; the type argument gives the fact one home, and the container is where the value and the hydrated row meet | A separate classifier field typed by the dictionary (keeps two homes and a selector column on every card); a head-side `Classifier` (with no classifier field it would have nothing to name, and the axis would be declared twice); a bare code on the container (the code is a storage fact, not a model one) |
| A new `DictionariesDomain` in the demo | A shared dictionary is not owned by one business domain, and the domain is what the sidebar shows | Putting it in `billing` (implies ownership for 21 other files); putting it outside any domain (the entity would have no domain edge) |

## Re-checked after Phase 1 design

Unchanged in cost: the design adds one internal module (`declared_values.py`), one public method (`to_reference`), one generic container (`Specialization[T, D]`) with a derived `declared_variant`, two graph properties (`properties.values`, `reference_qualname`), one removed graph property (`classifier_field`) and one client renderer. It adds no dependency, no storage migration, no route, and no new example series.
