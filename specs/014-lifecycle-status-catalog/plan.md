# Implementation Plan: Lifecycle statuses live on the state type, and the axis checks its whole vocabulary

**Branch**: `feature/issue-237-state-catalog-and-lifecycle-checks` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-lifecycle-status-catalog/spec.md`

## Summary

Since #209 one lifecycle axis is one class: the status objects are class attributes of the axis, `_template` holds the transitions, and `StateVocabulary` collects the statuses next to `Lifecycle`. The status type is a separate module-level class that carries only the fields. Two declaration mistakes pass silently: a declared status the axis never uses, and an equal-but-distinct instance accepted because membership is compared by fields.

The change moves the statuses to the type they belong to:

1. **The state type owns its statuses.** `OrderStateEntity` declares `DRAFT = OrderStateEntity(...)`, `PAID = ...` in its own body; after the class is created each name is a full instance, all fields are initialised by Pydantic, and the type carries the catalogue (`members`, `codes()`, `by_code()`, `entity_type`).
2. **The surface is the class name, and only the class name.** Inside a state type body the type's own name resolves to an internal declaration factory; the factory returns a placeholder, and a Pydantic post-model hook converts every placeholder into a real instance after the model is built. No `state(...)`, no `cast`, no `TYPE_CHECKING` appears in model code.
3. **The axis names the type once.** `class OrderLifecycle(Lifecycle[OrderStateEntity])` keeps only `_template`; the names in the template are `OrderStateEntity.DRAFT`, `OrderStateEntity.PAID`.
4. **Two refusals, at class creation.** A status that is not a declared object of the type (including an equal-but-distinct instance) raises `ForeignStateError`; a declared status the states never list raises `MissingStateError`. Coverage counts states only, never transition targets.
5. **The corpus migrates mechanically.** 55 axis declarations and 64 state types move in one phase; the status lines are copied unchanged, `StateVocabulary` is removed, and the 22 bare `Lifecycle` annotation sites are parameterised for `mypy --strict`. The entity field, the runtime and the graph do not change.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`). Eight packages under `packages/`; 43 example scripts with notebooks; the Maxitor TypeScript client is untouched.

**Primary Dependencies**: no new dependency. Pydantic v2 provides the post-model hook (`__pydantic_init_subclass__`) and `model_config["ignored_types"]` used by the placeholder; mypy, ruff, pylint and pytest are already configured.

**Storage**: N/A. The Maxitor DuckDB store reads the graph JSON; the state row is unchanged, so no table, column or persisted data moves.

**Testing**: `pytest` per package (`packages/*/tests`), `mypy --strict` across the eight packages, ruff, pylint, and the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial, per `AGENTS.md`: break the identity check, the coverage check, the hook conversion and the ignored-types entry one at a time, confirm the dedicated test fails and no other does, then restore.

**Target Platform**: the eight Python packages, the demo model under `packages/aoa-demo`, the examples and the notebooks. The Maxitor client and the graph wire format are consumers, not targets.

**Project Type**: library monorepo — `aoa-action-machine` changes the framework; `aoa-demo`, `examples/` and the framework's own tests migrate; `docs/` and the changelogs follow.

**Performance Goals**: no runtime cost. The placeholder conversion and both refusals run once per class at import; no code is added to construction, field access, graph traversal or Maxitor.

**Constraints**: no new dependency; every commit on the branch must leave the tree green; `mypy --strict` with `disallow_any_generics` means every bare `Lifecycle` annotation and all 55 axes are parameterised with no new `# type: ignore`; every new module keeps its principle-III header; new public symbols get AI-CORE blocks (principle IV) and one-line docstrings (principle V); all text in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 55 `(Lifecycle, StateVocabulary)` declarations (32 demo, 16 examples, 7 framework tests); 64 state types (32 demo, 24 examples, 8 framework tests); 110 `StateVocabulary` mentions across Python; 13 catalogue API call sites; 22 `Lifecycle` annotation lines across 9 files; 2 new exceptions; 1 deleted module; 1 new framework module (`state_spec.py`), 2 core framework modules edited (`state_entity.py`, `lifecycle.py`), plus `exceptions.py` and the domain facade; 4 new example steps with their notebooks; 1 tutorial, 1 reference page, 1 README section, 1 changelog article.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Six phases; each becomes a commit only on instruction. The mapping/measurement phase ends with the baseline shown; the migration starts only after the maintainer has seen it. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | New modules, the two exceptions, the tests, the docs and the changelog are English; the Russian drafts stay beside their pages, as the house rule requires. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | `state_spec.py` is written with the full header; `state_entity.py`, `lifecycle.py`, `exceptions.py` and `domain/__init__.py` keep or restore theirs as they are touched. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `BaseStateEntity` and `Lifecycle` get their blocks updated to the catalogue and the checks; `ForeignStateError` and `MissingStateError` get blocks. `StateSpec`, `state()` and `StateEntityMeta` are internal and carry no block; they get one-line docstrings. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol gets one: the hook, the metaclass, `members`, `codes()`, `by_code()`, `entity_type`, the two exceptions, every new test. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 4, 5 and 6 are those three steps in that order. No earlier phase absorbs them. |
| VI.5 each case twice | Every case as a script under `examples/` and as a notebook | The documentation phase adds `20_missing_status`, `21_twin_instance`, `22_status_fields` and `23_plain_lifecycle` under `examples/step_22_lifecycle/`, each as `.py` and `.ipynb`, and updates the existing foreign-status case; every case is executed while written. |

**Violations requiring justification**: none in the delivered state. Complexity Tracking records the alias and the generic sweep as deliberate costs, not violations.

**Re-checked after Phase 1 design**: unchanged. The design adds two public exception names and a generic parameter on `Lifecycle`; it adds no dependency, no module path outside `domain/`, and no change to the graph or Maxitor.

## Project Structure

### Documentation (this feature)

```text
specs/014-lifecycle-status-catalog/
├── plan.md                              # this file
├── spec.md                              # the specification
├── spec.ru_draft.md                     # its Russian draft (gitignored)
├── research.md                          # Phase 0: decisions, alternatives, measurements
├── data-model.md                        # Phase 1: state type, status, catalogue, axis, template
├── quickstart.md                        # Phase 1: runnable proof of every case
├── contracts/
│   ├── state-declaration-contract.md    # the surface, fields, catalogue, inheritance, typing
│   └── lifecycle-axis-contract.md       # the generic axis, the two refusals, plain Lifecycle
├── evidence/
│   ├── scan_lifecycle_catalog.py        # counts, coverage, per-axis/per-type dump
│   ├── baseline.before.json             # axes, statuses, template states, graph rows
│   ├── baseline.after.json
│   ├── compare_baselines.py             # SC-005 evidence: identical or a named difference
│   └── migrate_lifecycle_catalog.py     # the AST codemod: move statuses, drop the mixin, parameterise the axis
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── domain/
│   │   ├── state_spec.py              # NEW — StateSpec + the internal state(...) factory
│   │   ├── state_entity.py            # metaclass alias, ignored_types, conversion hook, catalogue
│   │   ├── lifecycle.py               # Lifecycle[StateT], _state_type, the two refusals
│   │   ├── state_vocabulary.py        # DELETED — its jobs split between the hook and Lifecycle
│   │   ├── exceptions.py              # ForeignStateError, MissingStateError
│   │   └── __init__.py                # StateVocabulary removed; the two errors exported
│   └── graph/nodes/…                  # annotations only, no behaviour
└── tests/action_machine/
    ├── domain/test_state_entity.py    # the surface, fields, catalogue, inheritance, alias
    ├── domain/test_lifecycle.py       # the generic axis on the existing fixtures
    └── domain/test_lifecycle_catalog_checks.py   # NEW — the two refusals, plain Lifecycle

packages/aoa-demo/src/aoa/demo/model/    # 32 axes, 32 state types migrate
examples/                                # 16 axes, 24 state types migrate; examples' scripts
packages/aoa-action-machine/tests/       # 7 axes, 8 state types; support fixtures
docs/tutorials/step-22-lifecycle.md      # the new declaration, the refusals, the fields
docs/reference/intents-and-invariants.md # the lifecycle FSM contract
README.md                                # the lifecycle section
examples/step_22_lifecycle/              # 20, 21, 22 — script + notebook; existing cases updated
docs/CHANGELOG.md, packages/*/CHANGELOG.md
```

**Structure Decision**: the framework change stays inside `aoa-action-machine/domain`: one new module for the placeholder and the internal factory, one edited module for the state kind, one edited module for the axis, two new exceptions and one deleted mixin. The demo, the examples and the framework's own tests change only their declarations. The graph nodes and the Maxitor store keep their behaviour; any edit there is a type annotation for the generic.

## Phases

Each phase is one commit, on instruction, and leaves the tree green.

| # | Phase | Outcome | Green because |
| --- | --- | --- | --- |
| 1 | Setup and baseline | Branch and environment confirmed; `scan_lifecycle_catalog.py` run; `baseline.before.json` records every axis, its status type, its statuses, its template and the demo graph rows; the counts in the spec are current | No code changes |
| 2 | The state type owns its statuses and its catalogue | `state_spec.py`; `StateEntityMeta.__prepare__` alias; `ignored_types`; `__pydantic_init_subclass__` conversion; `members`, `codes()`, `by_code()`, `entity_type`; tests for fields, defaults, duplicate codes, inheritance, the alias and the shadowing | The 55 existing axes still apply `StateVocabulary` and are untouched; the new surface is tested on new fixtures with a plain `Lifecycle` axis; `members` is empty on the existing state types, so nothing else changes |
| 3 | The corpus migrates | `state_vocabulary.py` deleted; 55 axes and 64 state types migrated; 13 catalogue call sites moved; the framework tests, the demo tests and the example scripts updated; the after-baseline compared | Every axis and every state type are on the new form (the axes stay plain `Lifecycle`); the old mixin has no user left; no new check is on yet, so nothing lawful is refused |
| 4 | The axis declares its type and the refusals land | `Lifecycle(Generic[StateT])`, `_state_type`, both refusals, the two exceptions; the 55 axes parameterised with their state types; 22 annotation sites parameterised; the new checks tests; the generic axis tests | Every axis is already migrated; this phase gives it its type parameter, so the refusals have an object to check and no plain axis remains |
| 5 | The check run (VI.1) | `bash scripts/run_checks_with_log.sh` taken to zero | It is the check |
| 6 | The documentation (VI.2) | `step-22` tutorial + `ru_draft`; the reference page + `ru_draft`; the README section; `20_missing_status`, `21_twin_instance`, `22_status_fields`, `23_plain_lifecycle` as script + notebook; the existing lifecycle examples and notebooks re-executed | Docs only; every example runs while it is written |
| 7 | The changelog (VI.3) | One article in `docs/CHANGELOG.md`; `[Unreleased]` entries for `aoa-action-machine` and `aoa-demo` | Text only |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The alias shadows a global with the same name as the state type, and the mistake is silent | Documented in the reference page and covered by a test: a body referencing a global named like the class receives the factory; any other unknown name still raises `NameError` |
| The Pydantic hook runs before the model is ready and constructs a fieldless instance | The hook is `__pydantic_init_subclass__`, not `__init_subclass__`; a test asserts that every field is present and that a misspelled field fails at class creation |
| `ignored_types` is dropped by a subclass that overrides `model_config` | The config is set on `BaseStateEntity`; a test subclass that overrides the config is asserted to preserve the placeholder exclusion, and removing the entry is a named adversarial break |
| The codemod moves a status to the wrong type, drops one, or misses one of the 55 axes | The baseline records every axis's statuses and template; `compare_baselines.py` reports a per-axis diff; the scan after migration reports 0 axes on `StateVocabulary` and 0 uncovered statuses |
| A generic sweep misses a bare `Lifecycle` annotation or hides it with `# type: ignore` | `mypy packages/` is the authority; the plan forbids new ignores; the review checks the diff for `type-arg` suppressions |
| Two axes share one state type and one of them is narrower | The coverage rule refuses the narrower axis with `MissingStateError`; the docs state that a narrowed axis declares its own state type |
| A status is used only as a transition target and the axis is accepted | A dedicated test: the target-only case raises `MissingStateError` |
| The twin message names an attribute that is inherited, not on the type's own `__dict__` | The message resolves the attribute name through the MRO; a test covers an inherited status |
| The graph changes because the state row is built from a different object | The baseline records the demo's state rows; `compare_baselines.py` compares labels, attributes and transitions; the entity field types are compared too |
| The check run's two accepted remarks are joined by a new one | Phase 5 fixes every remark except the two named in the constitution; the log tail is pasted if anything remains |
| The examples and notebooks drift from the scripts | Notebooks are re-executed in phase 6, never edited; the new cases are written as script and notebook together |
| The Russian drafts fall behind | The documentation phase writes the `ru_draft` beside each page; the report links both |

## Complexity Tracking

| Deliberate cost | Why needed | Simpler alternatives rejected because |
| --- | --- | --- |
| A metaclass with `__prepare__` that answers the class's own name with the declaration factory | The model author writes `DRAFT = OrderStateEntity(...)` inside `OrderStateEntity`; the class name is not bound while its body runs, so only the class namespace can make that surface work — and the surface is what gives the AI a typed declaration without `cast` and a mechanical migration | Public `state(...)` changes the surface and needs `cast`/`TYPE_CHECKING`; explicit post-class assignment moves the statuses out of the body and doubles the lines; a nested type in the axis keeps the catalogue on the axis and does not deliver the role split; the metaclass-created slot is more magic than a placeholder plus the documented Pydantic hook |
| The generic `Lifecycle[StateType]` and the parameterisation of 22 annotation sites | The axis must name its type; the type is the contract the refusals check. The generic form is the issue's example and was confirmed in clarify | The class keyword `Lifecycle, state_type=Type` gives the same checks without the sweep but was not the chosen form; a separate `TypedLifecycle` base would leave two axis bases |
| The migration lands before the refusals | The old mixin's foreign check dies with the mixin in phase 3; the new refusals need the generic axis and every axis migrated, which is phase 4. For one commit the axes carry no foreign or coverage check. | Landing everything in one commit was rejected for review size and because the generic sweep and the 55-axis codemod are independent changes; a coexistence bridge that keeps the old check alive for one commit was rejected as the second grammar the specification forbids |
| Identity, not equality, for membership | The current check accepts an equal-but-distinct instance, so the template can hold an object the catalogue does not expose; identity is the guarantee the contract states | `isinstance` alone would accept an undeclared instance of the right type; `==` is the defect being fixed |

## Re-checked after Phase 1 design

Unchanged: the design adds the two public exception names, the catalogue API on `BaseStateEntity`, and the generic parameter on `Lifecycle`; it adds no dependency, no storage change, and no graph or Maxitor change. The only new module is `domain/state_spec.py`; the only deleted module is `domain/state_vocabulary.py`.
