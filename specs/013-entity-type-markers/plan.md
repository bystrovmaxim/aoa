# Implementation Plan: Entity kinds — one base class per kind, and the kind in the name

**Branch**: `feature/issue-210-entity-type-markers` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-entity-type-markers/spec.md`

## Summary

An entity has one base today, `BaseEntity`, and that base says nothing about what an instance represents: an order, an order line, a technical link and a currency dictionary are written the same way, and the only name rule is a generic `…Entity` suffix. #209 added the first kind base class, `BaseStateEntity`, for lifecycle states.

The change adds the other five and gives all six the same shape:

1. **Six kind base classes, one file each.** `core_entity.py`, `assoc_entity.py`, `detail_entity.py`, `spec_entity.py`, `enum_entity.py` join `state_entity.py` in `domain/`. Each is `class BaseXxxEntity(BaseEntity, ABC)` and overrides `__init_subclass__` to hold its own descendants to its own name suffix.
2. **One place, no types.** No enum, no registry, no class attribute, no decorator. The entity base recognises a kind base class by inheritance plus an overridden hook; each kind base class derives its suffix from its own name (`BaseCoreEntity` → `CoreEntity`); the wire word is the same name without `Base` and `Entity` (`core`).
3. **Two rules in the base.** `BaseEntity.__init_subclass__` keeps the generic `*Entity` invariant, keeps a kind base class abstract and out of the model graph, and — once the corpus has moved — refuses direct inheritance from itself and two kind base classes in one chain.
4. **The kind on the wire.** Every entity row of the interchange graph carries `properties.entity_kind`; the graph JSON schema makes it required; the Maxitor DuckDB store keeps it in a column and returns it in the node payload.
5. **The corpus.** 476 classes migrate by meaning and are renamed — 209 in the demo, 145 in the examples, 114 in the framework's tests, 8 in the other packages — with a mapping table reviewed before the renames, one AST codemod applying them, and a baseline proving that no field, relation or lifecycle moved.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`; the repository already uses PEP 695 syntax in `graph/core/exclude_graph_model.py`). Eight packages under `packages/`, a TypeScript client under `packages/aoa-maxitor/client/`, 43 example scripts with notebooks under `examples/`.

**Primary Dependencies**: none new. Pydantic v2 is already the entity backend; the kind is the class name; the Maxitor store is DuckDB, already a dependency of `aoa-maxitor`.

**Storage**: DuckDB, where Maxitor keeps the loaded graph. The `entity` table gains `entity_kind VARCHAR NOT NULL`; the table is rebuilt from graph JSON on every load, so there is no persisted-data migration.

**Testing**: `pytest` per package (`packages/*/tests`), the Maxitor client build and typecheck, `task lint`, `task typecheck`, `task pylint`, the package-boundary and metadata checkers, the packaging smoke test, vulture, radon, and the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial, per `AGENTS.md`: every rule and every refusal is proved by breaking the code the way the test must catch, confirming that test fails and no other does, then restoring.

**Target Platform**: the eight Python packages plus the Maxitor TypeScript client. The demos, the examples and the documentation are consumers, not targets.

**Project Type**: library monorepo — `aoa-action-machine` gains the six kind base classes and the three base rules; `aoa-maxitor` gains the store column and the payload field; `aoa-demo`, the examples, `aoa-ocel`, `aoa-fastapi-adapter`, `aoa-mcp-adapter` are migrated; the docs and the changelogs follow.

**Performance Goals**: no measurable cost. The kind is read from the class's own name and its chain; the rules run once per class at import; no run-time path is added to field access, construction or graph traversal.

**Constraints**: no new dependency; every commit on the branch must leave the tree green, which fixes the order of the phases (the hierarchy refusals and the wire land after the migration); every new module keeps its principle-III header; the new classes get AI-CORE blocks (principle IV); every new symbol gets a one-line docstring (principle V); all text in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 6 new modules (one class each), 2 edited framework modules (`entity.py`, `state_entity.py` moves into the family), 1 domain facade extended, 1 graph node extended, 1 graph schema extended, 3 Maxitor store sites touched, 476 classes reclassified and renamed, 68 current-state non-Python files updated (43 notebooks re-executed, 21 markdown pages including `README.md` and its Russian draft, the 3-file generated artefact of one example, 1 TypeScript check script) while 25 historical files keep their names, 1 new example directory with its notebook, 1 reference page, 3 tutorials, 1 changelog article plus 2 package entries.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Nine phases; each becomes a commit only on instruction. The mapping phase ends with the table shown and a wait, before any rename is written. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | New modules, refusals, tests, docs and changelog are English; the Russian drafts stay beside their pages, as the house rule requires. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | The five new `*_entity.py` modules and the moved `state_entity.py` are written with the full header; `entity.py`, `entity_graph_node.py`, `graph_json_schema.py` and `domain/__init__.py` keep or restore theirs as they are touched. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | Each of the six kind base classes gets a block stating the role, the identity and the forbidden shapes from the issue; no block moves into a module docstring or onto a method. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol and every new test gets one; the six `__init_subclass__` hooks and the base hook get one line each; the debt in the touched files is paid as they are touched. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 7, 8 and 9 are those three steps in that order. No earlier phase absorbs them: the new example script is written in the documentation phase as VI.5 requires, and executed while it is written. |
| VI.5 each case twice | Every case as a script under `examples/` and as a notebook | The new `examples/step_28_entity_kinds/` ships `01_entity_kinds.py` and `01_entity_kinds.ipynb`; the six kinds, both refusals, the intermediate descendant and the mixin case are each a named step in both. |

**Violations requiring justification**: one, recorded in Complexity Tracking — the two hierarchy refusals and the wire property are switched on after the migration, so the branch carries two states (rules off, then on) even though the delivered state has one. The spec forbids a temporary allowance, and the refusal fails at class creation; ordering is the only way to keep every commit green.

**Re-checked after Phase 1 design**: unchanged. The design adds no dependency and no public name beyond the six kind base classes and the `entity_kind` row property the spec names. The Maxitor change is one column, one insert, one payload field.

## Project Structure

### Documentation (this feature)

```text
specs/013-entity-type-markers/
├── plan.md                 # this file
├── spec.md                 # the specification
├── spec.ru_draft.md        # its Russian draft (gitignored)
├── research.md             # Phase 0: decisions and their measurements
├── data-model.md           # Phase 1: kinds, base classes, rules, row, store table
├── quickstart.md           # Phase 1: how to prove the feature end to end
├── entity-kind-map.md      # the 476 decisions, rendered for review
├── contracts/
│   ├── entity-kind-declaration-contract.md
│   └── graph-entity-kind-contract.md
├── evidence/
│   ├── scan_entity_classes.py     # the scan behind every count in the spec
│   ├── scan.before.txt            # committed with phase 1
│   ├── entity_kind_map.py         # the decisions, as data the codemod consumes
│   ├── migrate_entity_kinds.py    # the AST codemod (renames + base classes)
│   ├── baseline.before.json       # fields / relations / lifecycles / description per class
│   ├── baseline.after.json
│   └── compare_baselines.py       # SC-005 evidence: identical or a named difference
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── domain/
│   │   ├── entity.py                 # BaseEntity: the generic suffix, kind-base recognition, both hierarchy rules
│   │   ├── core_entity.py            # NEW — BaseCoreEntity + its name rule
│   │   ├── assoc_entity.py           # NEW — BaseAssocEntity + its name rule
│   │   ├── detail_entity.py          # NEW — BaseDetailEntity + its name rule
│   │   ├── spec_entity.py            # NEW — BaseSpecEntity + its name rule
│   │   ├── enum_entity.py            # NEW — BaseEnumEntity + its name rule
│   │   ├── state_entity.py           # BaseStateEntity + its name rule + descendants kept out of the graph
│   │   └── __init__.py               # six kind base classes exported from the facade
│   └── graph/
│       ├── nodes/entity_graph_node.py        # properties["entity_kind"], derived from the class name
│       └── graph_json_schema.py              # entity_kind required, enum of six words
│
└── tests/action_machine/
    ├── domain/test_entity_kind.py            # NEW — the six classes, their rules, the base rules
    └── domain/test_entity.py                 # the generic naming invariant, unchanged behaviour

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py  # column, insert, payload
└── tests/                                                             # 12 fixture rows gain the kind

packages/aoa-demo/src/aoa/demo/model/        # 209 classes: one kind + the kind in the name
examples/step_21_relations/ … step_26_maxitor  # 145 classes, 43 scripts, 43 notebooks
packages/aoa-action-machine/tests/            # 114 classes, incl. tests/support/domain_model/
packages/aoa-ocel/, aoa-fastapi-adapter/, aoa-mcp-adapter/   # 8 classes
examples/step_28_entity_kinds/                # NEW — script + notebook (documentation phase)
docs/reference/intents-and-invariants.md      # six kinds, both rules, the wire word
docs/tutorials/step-20-entity.md              # the declaration now carries a kind
docs/tutorials/step-28-entity-kinds.md        # NEW — the tutorial of the new example
docs/CHANGELOG.md, packages/*/CHANGELOG.md    # the article and the package entries
```

**Structure Decision**: the framework change stays inside `aoa-action-machine`, and every kind is one file: six `*_entity.py` modules in `domain/`, each holding one class, its AI-CORE block and its name rule. The base keeps the generic suffix, recognises a kind base class by inheritance plus an overridden hook, and owns both hierarchy rules. The graph property is owned by the node and the schema, the store by `aoa-maxitor`. The corpus migration changes no module structure — only class names and base classes.

## Phases

Each phase is one commit, on instruction, and leaves the tree green.

| # | Phase | Outcome | Green because |
| --- | --- | --- | --- |
| 1 | Setup | Branch and environment confirmed; the corpus scan re-run against the committed before-numbers | No code changes |
| 2 | The base recognises a kind base class | `BaseEntity.__init_subclass__`: a class that inherits the base directly and overrides the hook is excluded from the graph and cannot be instantiated; the generic `*Entity` rule stays | Nothing inherits the base differently yet, so no unmigrated class is affected |
| 3 | Six kind base classes, one file each | The five new modules plus the state one; each derives its suffix from its own name and checks its descendants; the facade exports all six; the test module covers the six and the base rules | Nothing inherits the new classes yet; the state classes already carry their suffix |
| 4 | The mapping table | `entity-kind-map.md` (476 rows with a reason), `entity_kind_map.py`, `baseline.before.json`, the compare script | Artifacts only; shown and waited on before any rename |
| 5 | The corpus migrates | The 114 framework fixtures, the 209 demo classes, the 145 example classes with their notebooks and artefacts, the 8 classes in the other packages, the 21 pages and `README.md`; the after-baseline and the scan | Imports and every suite pass as before |
| 6 | The rules switch on, the kind goes on the wire | The two hierarchy refusals; `properties.entity_kind` in the node and the schema; the store column; the 14 fixture rows; the round-trip test | Every class carries a kind, so the rules refuse nothing lawful and every row can state its kind |
| 7 | The check run (VI.1) | `bash scripts/run_checks_with_log.sh` taken to zero | It is the check |
| 8 | The documentation (VI.2) | The reference page, two tutorials, the new `step_28` script and notebook, the Russian drafts, the regenerated pages of the renamed classes | Docs only; the examples run while written |
| 9 | The changelog (VI.3) | One article in `docs/CHANGELOG.md`; `[Unreleased]` entries for `aoa-action-machine` and `aoa-demo` | Text only |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A seventh class inherits the base directly and overrides the hook, silently becoming a kind base class | A test scans `packages/` and asserts exactly six such classes |
| A kind base class is renamed, changing its suffix and its wire word | The suffix rule and the word both come from the name, so the rename either keeps the convention or the six tests fail; the map review covers the corpus |
| A marker chosen by table shape rather than by meaning — an offer that looks like a join table becomes `assoc` and loses its price in the drawing | The map's reason column states what the instance represents; the maintainer reviews 476 rows before the codemod runs (phase 4) |
| A rename that collides inside one module (three `DummyEntity`, two `ChildEntity`) | The codemod resolves by module and refuses on a collision; the class keeps a distinct name per kind |
| The baseline comparison passes because it compares nothing | The baseline records per class the field, relation and lifecycle names; `compare_baselines.py` reports the per-class diff, and the migration is broken on purpose once to see the comparison fail |
| The stricter schema is satisfied by the builder but not by hand-written fixture rows | Phase 6 updates the 14 measured rows and asserts that the schema **rejects** a row without the kind |
| Notebook output that no longer matches its script | Notebooks are re-executed in phase 5, never edited; the docs phase re-runs the new example while writing it |
| The 476-class diff hides a lost field | `baseline.after.json` + `compare_baselines.py`, and the demo's graph entity/field/relation counts (SC-005, SC-006) |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| The hierarchy refusals and the wire property are off for phases 1–5 and on from phase 6, so the branch has two states | The refusals fail at class creation: with them on, the unmigrated 476 classes do not import, and no commit before the migration ends would be green | A temporary allowance list was rejected in the specification: it is a second, quieter grammar, and the spec forbids it |
