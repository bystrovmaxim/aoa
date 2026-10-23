# Implementation Plan: explicit entity relations, a protected dictionary member, resolvable schemas, and a card that shows labels

**Branch**: `feature/issue-249-explicit-relations-and-dictionary-safety` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-explicit-entity-relations/spec.md`

## Summary

A field whose type is another entity is accepted as a scalar: the model builds, the graph gets a column, and no relation exists. The same declaration surface carries three confirmed defects measured at `2e70a30d` — a dictionary member becomes mutable when a validator returns a list, a member whose runtime type disagrees with its annotation exports a shape its schema does not describe, and the serialization schema of an `Enum` property raises `KeyError '#/$defs/Grade'`. A fourth defect puts the relation's description text into the field's default slot, so the field becomes omittable and an entity carries an unvalidated marker object.

The change has six work items and nine phases:

1. **An entity-typed field is declared explicitly.** A new boundary validator refuses a bare structural-entity field, a collection of one, and a bare `X | None`, naming the two legal forms; `NoRelation(reason)` is added as the embedded-value marker; a state-typed field is refused with the `Lifecycle[...]` form as its only answer.
2. **`Classifier` stops restating the field name.** The `field` argument leaves the marker and its comparison check leaves the validator; 165 declarations in 52 files and 111 occurrences across 39 notebooks migrate.
3. **The dictionary card shows labels.** The enum kind's field list loses `code` and `display_name`, the value row loses its code cell, and the code becomes a tooltip — the graph and the payload keep both.
4. **A dictionary member is checked after user validation.** The completed member is verified against the declared annotation and the immutable type set, before it joins the catalogue, including `Enum` values and nested tuples.
5. **The serialization schema stays self-contained.** Definitions survive the reference projection, and `properties.required` describes what is actually emitted.
6. **A relation's description is metadata.** `Rel` is removed, `FieldInfo.description` becomes the one description source, the default contract is enforced at the same boundary as item 1, and 262 declarations plus the hydration callers migrate.

Phases 1–6 are the work items, phase 7 is the check run, phase 8 the documentation, phase 9 the changelog.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"`, runtime measured 3.12.12); Pydantic 2.12.5 supplies `model_fields`, the core-schema hooks and `GenerateJsonSchema`; TypeScript with Vite for the Maxitor client.

**Primary Dependencies**: no new dependency. `jsonschema>=4.17` already validates payloads and schemas in `aoa-action-machine`; `@hpcc-js/wasm-graphviz` already renders the SVG in the client checks; Pydantic's public `GenerateJsonSchema` and `CoreSchema` types are already used by `BaseEnumEntity`.

**Storage**: none. The graph document keeps the dictionary code and label, so a saved graph renders without a rebuild and no migration exists.

**Testing**: `pytest` per package; `mypy --strict`; `task lint`, `task pylint`, `task cc`, `task mi`, `task dead`; the package-boundary and package-metadata checkers; the wheel build and the packaging smoke test; the client build and the three Node checks; the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial per `AGENTS.md`: reintroduce each corrected defect in isolation, confirm its test fails and no unrelated test does, restore.

**Target Platform**: `aoa-action-machine` (relation markers, the graph build boundary, `enum_entity`, the two intent resolvers, the hydration docstring), `aoa-maxitor` (payload action, payload schema, `buildDotSource.ts`, three client checks), `examples/`, `docs/` and the notebooks.

**Project Type**: library monorepo plus one viewer; the change is a framework change, a declaration migration, one payload projection and one renderer row.

**Performance Goals**: no runtime cost. The new field check walks `model_fields` once per graph build, in the pass that already walks them for specialization; the member check runs once per dictionary class at import; the schema fix changes no generation count; the card change removes two payload rows and one cell.

**Constraints**: one commit per phase, each leaving the tree green — which forces the `Classifier` migration (phase 2) and the `Rel` migration (phase 6) to carry their whole corpus in the same commit; `Rel` leaves the public surface with no deprecation window (FR-031), so phase 6 migrates every declaration, notebook and page it names; every new symbol keeps its module header (III), AI-CORE block (IV) and a one-line docstring (V); English throughout (II); nothing is committed without instruction (I).

**Scale/Scope**: 6 work items; 262 `= Rel(description=…)` declarations in 58 files (7 nullable) and 170 occurrences across 44 notebooks; 165 `Classifier(field=…)` occurrences in 52 Python files and 111 occurrences across 39 notebooks; 1 new marker; 1 new validator module wired into `NodeGraphCoordinator.build()`; 2 intent resolvers; 1 payload action; 1 payload schema; 1 client renderer; 3 client checks; 7 documentation pages; 2 package changelogs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Nine phases, each a commit only on instruction; nothing is pushed. The branch exists on the maintainer's word. |
| II. English in commits and code | Every message, comment, docstring, refusal and page in English | Refusal texts, tests, pages and the changelog are English; the phase rules quote the refusal text in English. |
| III. Module headers | Path on line 1, title docstring, ruled sections | The new validator module opens with its path and the rule it enforces; `relation_markers.py`, `enum_entity.py`, `entity_specialization_validator.py`, the two resolvers and the payload action keep their headers and are edited inside them. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `NoRelation` gains one; `Classifier`'s block loses `field`; `Rel`'s block is deleted with the class; `BaseEnumEntity`'s block gains the runtime member check; the new validator function gains one. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol: the marker, the validator, the field walker, the member check, each new test, each new case example. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 7, 8 and 9 are those three, in that order; no earlier phase absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | Phase 8 adds the cases this change introduces — the refused bare field, the embedded-value marker, the refused state field, the mutable member, the resolvable schema, the description in a default — as scripts and notebooks beside the existing relation and dictionary series, and executes each while writing. |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` green, only the two accepted remarks | Phase 7 runs it, fixes every remark it reports, and records the tail. |

**Violations requiring justification**: none. Complexity Tracking records the public-API removal of `Rel`, the new build-time refusal, and the payload projection as deliberate costs.

**Re-checked after Phase 1 design**: unchanged. The design removes more than it adds: one marker class deleted, one marker argument deleted, two fallback branches deleted, two payload rows and one renderer cell deleted; added are one marker, one validator module, one member check and one definition-preserving schema path.

## Project Structure

### Documentation (this feature)

```text
specs/017-explicit-entity-relations/
├── plan.md                          # this file
├── spec.md                          # the specification
├── research.md                      # Phase 0: D1–D11, prototypes and measured counts
├── data-model.md                    # Phase 1: the field forms, the member, the schema, the card
├── quickstart.md                    # Phase 1: the runnable proofs, eleven of them
├── contracts/
│   ├── entity-field-declaration.md  # the two legal forms, the refusals, the state answer
│   ├── relation-field-metadata.md   # the default contract table and the description rule
│   └── dictionary-member.md         # the supported types, the runtime check, the enum rule
└── tasks.md                         # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── domain/
│   ├── relation_markers.py              # NoRelation added; Rel removed
│   ├── specialization_containers.py     # Classifier.field removed
│   ├── enum_entity.py                   # _emitted_reference_schema preserves definitions
│   ├── declared_values.py               # the runtime member check beside the annotation check
│   └── hydration.py                     # the docstring stops advertising a relation default
├── graph/
│   ├── core/node_graph_coordinator.py   # the new field pass runs beside the specialization pass
│   └── validators/
│       ├── entity_field_validator.py    # new: legal forms, refusals, default contract
│       └── entity_specialization_validator.py  # the Classifier.field comparison removed
└── intents/entity/
    ├── entity_relation_intent_resolver.py          # one description rule
    └── entity_specialization_intent_resolver.py    # the same rule

packages/aoa-action-machine/tests/
├── action_machine/domain/               # member safety, schemas, markers, hydration
├── action_machine/graph/                # the field validator, specializations
└── support/domain_model/entities.py     # migrated declarations

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action.py   # enum field rows omitted
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py
├── client/src/lib/buildDotSource.ts                                 # the code becomes a tooltip
├── client/scripts/check-erd-dictionary-values.ts                    # the printed text and the tooltip
└── tests/                                                           # the payload test

examples/step_20_dictionaries/          # the new cases as scripts
examples/step_21_relations/             # the new cases as scripts
docs/                                   # the pages the old forms name
```

**Structure Decision**: the change follows the repository's existing split — declaration rules in `domain/`, graph-boundary checks in `graph/validators/`, the display in `packages/aoa-maxitor`, and the corpus under `packages/`, `examples/` and `docs/`. No new package, no new layer, and no new dependency.

## Phases

Each phase is one commit on instruction, leaves the tree green, and carries its own regression evidence.

### Phase 1 — An entity-typed field is declared explicitly

Add `NoRelation(reason)` to `relation_markers.py` with its AI-CORE block, a nonblank reason, frozen slots and equality, export it from `domain/__init__.py`, and keep it distinct from `NoGraphEdge()`. Add `graph/validators/entity_field_validator.py` with one public `validate_entity_fields()` that walks the `@entity` classes (reusing `declared_entity_classes()`), skips `exclude_graph_model` classes, and for each resolved field: accepts a relation container, accepts `NoRelation` on the exact entity type or on `X | None`, and refuses a bare structural entity, a collection of one, a bare `X | None` of one, and a state entity — with a message naming owner, field, resolved type and the legal forms. Forward references are checked on the resolved annotation only; a field with an unresolvable string annotation is left to the existing unresolved-name failure instead of being called scalar. Wire the pass into `NodeGraphCoordinator.build()` next to `validate_entity_specializations()`.

Exit: the four forms have a test each; a model with a refused form fails `build()`; the corpus builds unchanged (0 bare fields measured).

### Phase 2 — `Classifier` states only the variant

Remove `field` from `Classifier.__init__`, its slots, its AI-CORE block and every use; delete the `marker.field != field_name` comparison in `entity_specialization_validator.py` while keeping the head-side refusal, the inverse check, dictionary membership, closure and cycles. Migrate the 165 occurrences in 52 files and the 111 notebook occurrences in the same commit. A stray `field=` raises `TypeError` from the constructor, which is the refusal FR-035 asks for.

Exit: the remaining specialization checks each fail a test when broken; the corpus builds with 0 `field=` arguments.

### Phase 3 — The dictionary card shows labels

In `list_entities_action.py`, for the enum kind drop `code` and `display_name` from the payload's field list; leave the graph SQL and `graph_json_schema.py` untouched. In `buildDotSource.ts`, drop the code cell and put `TOOLTIP="code: …"` on the value row's label cell, following the tooltip the specialization axis row already uses. Update `check-erd-dictionary-values.ts` to assert the printed text has no code and the DOT carries the tooltip, add the payload test, and reconcile `specs/016-value-declaration-consistency/contracts/dictionary-card.md` §3 to the final behaviour.

Exit: the three client checks pass; the payload schema still validates; an old graph renders.

### Phase 4 — A dictionary member is checked after user validation

Keep `_require_immutable_properties()` as the annotation-time rule and add a runtime check in `declared_values.py` after each member is constructed and before `cls.members` is published: every property's runtime value must match its declared annotation and satisfy the immutable set recursively, with tuples, `Enum` values and nested containers covered. Refuse — never freeze — with the dictionary, member, property path and actual type. `BaseStateEntity` is untouched.

Exit: the reproducer fails at declaration; a validator returning a valid tuple still publishes; editing an export changes nothing.

### Phase 5 — The serialization schema keeps its definitions

Rework `BaseEnumEntity._emitted_reference_schema()` so the property fragments keep the `$defs` they reference, using Pydantic's generation for the model's own property types rather than a fragment copy. Give the nested `properties` object a `required` list derived from the emitted shape — present-but-nullable stays required, an excluded field does not — and keep the input schema exactly as it is.

Exit: the `KeyError` reproducer returns a schema; the real export validates; a disallowed enum value is refused; every local `$ref` resolves.

### Phase 6 — A relation's description is metadata

Delete `Rel` and its export, extend `entity_field_validator.py` with the relation-default and description rules from `contracts/relation-field-metadata.md`, and make both intent resolvers read `FieldInfo.description` only. Migrate 262 declarations to `Field(description=…)`, deciding each of the 7 nullable relations by its full-construction call sites, update `test_hydration.py` where it asserted the leaking default, and migrate the notebooks and pages.

Exit: the four rows of the default table each have a test; a `Rel` import fails; a factory is refused without being invoked; both description syntaxes reach both edge kinds.

### Phase 7 — The closing check run

`bash scripts/run_checks_with_log.sh` to zero, including the client build, the three Node checks, mypy, pylint, radon, vulture, packaging and every package's tests. Only the chunk-size advisory and the pending-deprecation warning remain, and the tail is reported.

### Phase 8 — The documentation

The relation and specialization chapters, the dictionary chapter, `docs/reference/intents-and-invariants.md`, `docs/reference/glossary.md` and the how-to page on a failed specialization: each new refusal gets a case, and each case appears as a script under `examples/` and as a notebook, executed while written. No Russian draft is created.

### Phase 9 — The changelog

One article per affected package in `docs/CHANGELOG.md` — what a reader can now do, the two legal forms, the member guarantee, the resolvable schema and the card that no longer prints codes — without a per-file account.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The new refusal breaks a declaration the corpus really uses | The baseline measured 0 bare fields; phase 1 runs the full package suite and the demo before it is committed, and an unsupported form reports instead of skipping silently. |
| `Rel` removal leaves a stale notebook or page | The inventory is refreshed at the start of phase 6 with the same grep that produced 262; notebooks are executed, not inspected, and a stale import fails loudly. |
| A nullable relation loses its callers | Phase 6 decides each of the 7 by its full-construction call sites, per the spec's rule; a required field that keeps being omitted fails a test rather than silently changing behaviour. |
| The member check is too strict and refuses a working dictionary | The check accepts values equal to their annotation; the full package suite and the demo's dictionaries run in the same phase, and the adversarial reintroduction proves the check still catches the list. |
| The card change contradicts the #244 contract | Phase 3 updates that contract in place instead of adding a second one, and the payload test drives the server payload through the renderer. |
| A schema fix flattens or disables enums | The acceptance set is generated against a real export, a disallowed enum value, two definitions with the same short name and a custom serializer, per FR-018 and FR-020. |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| A new build-time refusal with no fallback | A graph that silently misdescribes the model is worse than a build that stops (FR-001) | Accepting the bare form with a warning keeps the defect and the false column |
| Removing `Rel` outright | A description object in the default slot is the defect; a compatibility path keeps two description carriers (FR-031) | A deprecation window would let a new declaration adopt the broken form |
| A payload projection for the enum kind only | The graph and reference exports must keep the code (FR-037) | Stripping the code at the source would break reference exports and graph data |
| One validator shared by two rules | Field forms (phase 1) and relation defaults (phase 6) are checked on the same resolved boundary | Two walkers would drift, exactly as the two `_field_description_hint()` copies did |

## Re-checked after Phase 1 design

The design keeps every gate green. It adds one marker, one validator module, one member check and one definition-preserving schema path, and removes one marker class, one marker argument, two fallback branches, two payload rows and one renderer cell. No gate moves to a violation, and Complexity Tracking's four entries are the deliberate costs above.
