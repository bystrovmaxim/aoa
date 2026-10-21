# Implementation Plan: Entity type markers — one base per kind, and the kind in the name

**Branch**: `feature/issue-210-entity-type-markers` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-entity-type-markers/spec.md`

## Summary

An entity has one base today, `BaseEntity`, and that base says nothing about what an instance represents: an order, an order line, a technical link and a currency dictionary are written the same way, and the only name rule is a generic `…Entity` suffix. #209 added the first marker, `BaseStateEntity`, for lifecycle states.

The change adds the other five markers and gives all six the structural rules they share:

1. **Six markers.** `BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity`, `BaseEnumEntity` join `BaseStateEntity`; each is `class BaseXxxEntity(BaseEntity, ABC)` carrying one decorator that registers its kind, keeps it out of the model graph and refuses instantiation.
2. **One registry.** `EntityKind` names the six kinds with their suffix (`CoreEntity` …) and their wire word (`core` …). It imports no marker, so `state_entity.py` and the new `entity_markers.py` both register into it without a cycle.
3. **Three refusals.** At `@entity` the declaration must have exactly one marker in its MRO and its name must carry that marker's kind — `DeclarationStructureError` for the structure, `NamingSuffixError` for the name. At `BaseStateEntity.__init_subclass__` a status type must be named `…StateEntity`, because status classes carry no `@entity`.
4. **The kind on the wire.** Every entity row of the interchange graph carries `properties.entity_kind`; the graph JSON schema makes it required; the Maxitor DuckDB store keeps it in a column and returns it in the node payload.
5. **The corpus.** 476 classes migrate by meaning and are renamed — 209 in the demo, 145 in the examples, 114 in the framework's tests, 8 in the other packages — with a mapping table reviewed before the renames, one AST codemod applying them, and a baseline proving that no field, relation or lifecycle moved.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`; the repository already uses PEP 695 syntax in `graph/core/exclude_graph_model.py`). Eight packages under `packages/`, a TypeScript client under `packages/aoa-maxitor/client/`, 43 example scripts with notebooks under `examples/`.

**Primary Dependencies**: none new. Pydantic v2 is already the entity backend; `EntityKind` is a `StrEnum` from the standard library; the Maxitor store is DuckDB, already a dependency of `aoa-maxitor`.

**Storage**: DuckDB, where Maxitor keeps the loaded graph. The `entity` table gains `entity_kind VARCHAR NOT NULL`; the table is rebuilt from graph JSON on every load, so there is no persisted-data migration.

**Testing**: `pytest` per package (`packages/*/tests`), the Maxitor client build and typecheck, `task lint`, `task typecheck`, `task pylint`, the package-boundary and metadata checkers, the packaging smoke test, vulture, radon, and the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial, per `AGENTS.md`: every new refusal is proved by breaking the code the way the test must catch, confirming that test fails and no other does, then restoring.

**Target Platform**: the eight Python packages plus the Maxitor TypeScript client. The demos, the examples and the documentation are consumers, not targets.

**Project Type**: library monorepo — `aoa-action-machine` gains the six markers, the registry and the refusals; `aoa-maxitor` gains the store column and the payload field; `aoa-demo`, the examples, `aoa-ocel`, `aoa-fastapi-adapter`, `aoa-mcp-adapter` are migrated; the docs and the changelogs follow.

**Performance Goals**: no measurable cost. Registration happens once at import; the decorator runs once per class; the node reads a registry lookup it already has the class for. No run-time path is added to field access, construction or graph traversal.

**Constraints**: no new dependency; every commit on the branch must leave the tree green, which fixes the order of the phases (the refusal lands after the migration); every new module keeps its principle-III header; the new public types get AI-CORE blocks (principle IV); every new symbol gets a one-line docstring (principle V); all text in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 1 new registry module, 1 new markers module, 2 edited framework modules (`entity.py` is untouched; `entity_decorator.py` and `state_entity.py` change), 1 domain facade extended, 1 graph node extended, 1 graph schema extended, 3 Maxitor store sites touched, 476 classes reclassified and renamed, 68 current-state non-Python files updated (43 notebooks re-executed, 21 markdown pages (among them `README.md` and its Russian draft, and 8 drafts), the 3-file generated artefact of one example, 1 TypeScript check script) while 25 historical files keep their names, 1 new example directory with its notebook, 1 reference page, 3 tutorials, 1 changelog article plus 2 package entries.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Eleven phases; each becomes a commit only on instruction. Phase 3 ends with the mapping table shown and a wait, before any rename is written. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | New modules, refusals, tests, docs and changelog are English; the two Russian pages this change rewrites keep their `_draft.md` drafts beside them, as the house rule requires. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | `domain/entity_kind.py` and `domain/entity_markers.py` are new and are written with the full header; `entity_decorator.py`, `state_entity.py`, `entity_graph_node.py`, `graph_json_schema.py` and `domain/__init__.py` keep or restore theirs as they are touched. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | Each of the six markers gets a block stating the role, the identity and the forbidden shapes from the issue; `EntityKind` gets one; no block moves into a module docstring or onto a method. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol and every new test gets one; the debt in the files touched is paid as they are touched. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 9, 10, 11 are those three steps in that order. No earlier phase absorbs them: the new example script is written in the documentation phase as VI.5 requires, and executed while it is written. |
| VI.5 each case twice | Every case as a script under `examples/` and as a notebook | The new `examples/step_28_entity_kinds/` ships `01_entity_kinds.py` and `01_entity_kinds.ipynb`; the six kinds, the three refusals, the exempt intermediate and the marker-as-target case are each a named step in both. |

**Violations requiring justification**: one, recorded in Complexity Tracking — the rule is switched on in phase 8, after the migration, so the branch carries two states (rule off, then rule on) even though the delivered state has one. The spec forbids a temporary allowance, and the refusal fails at class definition; ordering is the only way to keep every commit green.

**Re-checked after Phase 1 design**: unchanged. The design adds no dependency and no public name beyond the six markers, `EntityKind` and the `entity_kind` row property the spec names. The Maxitor change is one column, one insert, one payload field.

## Project Structure

### Documentation (this feature)

```text
specs/013-entity-type-markers/
├── plan.md                 # this file
├── spec.md                 # the specification
├── spec.ru_draft.md        # its Russian draft (gitignored)
├── research.md             # Phase 0: eleven decisions and their alternatives
├── data-model.md           # Phase 1: kinds, markers, rules, row, store table
├── quickstart.md           # Phase 1: how to prove the feature end to end
├── entity-kind-map.md      # the 476 decisions, rendered for review (phase 3)
├── contracts/
│   ├── entity-kind-declaration-contract.md
│   └── graph-entity-kind-contract.md
├── evidence/
│   ├── scan_entity_classes.py     # the scan behind every count in the spec
│   ├── entity_kind_map.py         # the decisions, as data the codemod consumes
│   ├── migrate_entity_markers.py  # the AST codemod (renames + marker bases)
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
│   │   ├── entity_kind.py            # NEW — EntityKind, registry, kind_of(), markers()
│   │   ├── entity_markers.py         # NEW — the five new markers + @abstract_marker
│   │   ├── state_entity.py           # the marker registers its kind; the suffix rule lands here
│   │   ├── entity.py                 # untouched (the generic *Entity invariant stays)
│   │   └── __init__.py               # six markers and EntityKind exported from the facade
│   ├── intents/entity/
│   │   └── entity_decorator.py       # the two structural refusals and the suffix refusal
│   └── graph/
│       ├── nodes/entity_graph_node.py        # properties["entity_kind"]
│       └── graph_json_schema.py              # entity_kind required, enum of six words
│
└── tests/action_machine/
    ├── domain/test_entity_kind.py            # NEW — kinds, registry, abstractness, exclusion
    ├── domain/test_entity_markers.py         # NEW — the refusals, adversarially
    ├── domain/test_entity.py                 # the markerless @entity case inverts
    └── domain/test_state_entity.py           # the status suffix refusal

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py  # column, insert, payload
└── tests/                                                             # 12 fixture rows gain the kind

packages/aoa-demo/src/aoa/demo/model/        # 209 classes: one marker + the kind in the name
examples/step_21_relations/ … step_26_maxitor  # 145 classes, 43 scripts, 43 notebooks
packages/aoa-action-machine/tests/            # 114 classes, incl. tests/support/domain_model/
packages/aoa-ocel/, aoa-fastapi-adapter/, aoa-mcp-adapter/   # 8 classes
examples/step_28_entity_kinds/                # NEW — script + notebook (phase 10)
docs/reference/intents-and-invariants.md      # six kinds, three rules, the wire word
docs/tutorials/step-20-entity.md              # the declaration now carries a kind
docs/tutorials/step-28-entity-kinds.md        # NEW — the tutorial of the new example
docs/CHANGELOG.md, packages/*/CHANGELOG.md    # the article and the package entries
```

**Structure Decision**: the framework change stays inside `aoa-action-machine`, split across the three modules that own the concerns — a registry (`entity_kind.py`), the markers (`entity_markers.py`), the declaration rules (`entity_decorator.py`, `state_entity.py`). The graph property is owned by the node and the schema, the store by `aoa-maxitor`. The corpus migration is not a structural change: no module moves, no package boundary moves, only class names and bases.

## Phases

Each phase is one commit, on instruction, and leaves the tree green.

| # | Phase | Outcome | Green because |
| --- | --- | --- | --- |
| 1 | Six markers and the registry | `EntityKind`, `abstract_marker`, the five markers, `BaseStateEntity` registered, six names on the facade; tests for abstractness, exclusion from the graph, refusal of instantiation | The rule is not enforced yet, so the 476 declarations still import |
| 2 | The kind on the wire | `properties.entity_kind` in `EntityGraphNode`; the schema requires it; the Maxitor `entity` table, insert and payload carry it; 14 fixture rows and one exact-properties assertion updated | Every row the builder produces has the property, so the stricter schema validates |
| 3 | The mapping table | `entity-kind-map.md` (476 rows with a reason), `entity_kind_map.py`, `baseline.before.json`, the scan and compare scripts | Adds artifacts only; shown and waited on before any rename |
| 4 | Framework fixtures migrate | The 114 classes in `packages/aoa-action-machine/tests`, including the shared `tests/support/domain_model/` | Imports, the framework suite and the graph builds pass as before |
| 5 | The demo migrates | The 209 classes in `packages/aoa-demo/src/aoa/demo/model/` (17 bounded contexts) | The demo suite, its graph build and its ERD counts pass |
| 6 | The examples migrate | The 145 classes in 43 scripts; the 43 notebooks re-executed; the one example's `.dot`/`.json`/`.svg` regenerated; the 21 current-state pages and `README.md` updated by hand where the codemod cannot reach | Every example script runs and prints the regenerated output |
| 7 | The other packages migrate | 8 classes in `aoa-ocel`, `aoa-maxitor`, `aoa-fastapi-adapter`, `aoa-mcp-adapter`; `baseline.after.json` and the comparison | Their suites pass; the comparison shows 0 changed fields |
| 8 | The rule switches on | The three refusals in the decorator and the status suffix in `BaseStateEntity.__init_subclass__`; the markerless-`@entity` test inverts; the adversarial test module | The corpus is migrated, so nothing lawful is refused |
| 9 | The check run (VI.1) | `bash scripts/run_checks_with_log.sh` taken to zero | It is the check |
| 10 | The documentation (VI.2) | The reference page, two tutorials, the new `step_28` script and notebook, the Russian drafts, the regenerated pages of the renamed classes | Docs only; the examples run while written |
| 11 | The changelog (VI.3) | One article in `docs/CHANGELOG.md`; `[Unreleased]` entries for `aoa-action-machine` (the markers, the refusals) and `aoa-demo` (the renames) | Text only |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A marker chosen by table shape rather than by meaning — an offer that looks like a join table becomes `assoc` and loses its price in the drawing | The map's reason column states what the instance represents; the maintainer reviews 476 rows before the codemod runs (phase 3) |
| A rename that collides inside one module (three `DummyEntity`, two `ChildEntity`) | The codemod resolves by module and refuses on a collision; the class keeps a distinct name per kind |
| The baseline comparison passes because it compares nothing | The baseline records per class the field, relation and lifecycle names; `compare_baselines.py` reports the per-class diff, and the migration is broken on purpose once to see the comparison fail |
| The stricter schema is satisfied by the builder but not by hand-written fixture rows | Phase 2 updates the 14 measured rows and asserts that the schema **rejects** a row without the kind |
| Notebook output that no longer matches its script | Notebooks are re-executed in phase 6, never edited; the docs phase re-runs the new example while writing it |
| A commit before phase 8 claims a rule that is not on yet | The spec's "two states on the branch" note (Assumptions) and Complexity Tracking; the delivered branch is the only state that matters |
| The 476-class diff hides a lost field | `baseline.after.json` + `compare_baselines.py`, and the demo's graph entity/field/relation counts (SC-005, SC-006) |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| The rule is off for phases 1–7 and on from phase 8, so the branch has two states | The refusal fails at class definition: with the rule on, the unmigrated 476 classes do not import, and no commit before the migration ends would be green | A temporary allowance list was rejected in the specification: it is a second, quieter grammar, and the spec's FR-012 forbids it |
