# Implementation Plan: Lifecycle states as objects, read by the chain, the graph and the diagrams

**Branch**: `feature/issue-209-state-vocabularies` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-lifecycle-state-vocabularies/spec.md`

## Summary

A lifecycle state is two string literals today, `.state("payment_pending", "Payment pending")`. The label is stored in `StateInfo` and never leaves the template: the graph state row's `label` is the key, and the FSM payload's `display_name` is read from that label, so Maxitor draws `payment_pending`. There is also nowhere to put anything a status knows about itself.

The change introduces one object — a state entity — and makes the chain, the graph and the diagrams read it:

1. **The object.** `BaseStateEntity(BaseEntity)` with a required `code`, a required `display_name`, and any domain fields the status needs. Immutable, non-blank, kept out of the model graph.
2. **The axis class.** `StateVocabulary` is a mixin applied on the same declaration as `Lifecycle`: it collects the class's status attributes in declaration order, guarantees unique codes, exposes them by code, and checks that every status in `_template` is one of them.
3. **The chain.** The statuses and the links are declared in one class body: `.state(status)` and `.to(status, …)` take objects, the label comes from the object, classification and transitions stay in `_template`, and the string form is removed at the end of the branch. The class keeps the objects, so `get_state_entity(code)` can hand a status to whoever asks.
4. **The graph.** The state row keeps its id and kind, takes its label from the status, and carries all declared fields as `attributes`.
5. **Maxitor.** The diagram store keeps the attributes, the FSM snapshot reports the human label and orders by the declared order, and the DOT source uses the declared colour with a fallback to today's palette.
6. **The corpus.** 32 lifecycle declarations (28 chains and 4 private cycle sketches), 90 `.state(...)` and 65 `.to(...)` calls in `aoa-demo`, plus the framework tests, the examples and the documentation examples, because the string form disappears.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`), eight packages under `packages/`.

**Primary Dependencies**: none new. `pydantic` v2 is already the entity backend; `model_dump(mode="json")` is the serialization used for the attributes. No new library.

**Storage**: DuckDB, where Maxitor keeps the loaded graph. The `state` table gains an `attributes JSON` column; the `nodes` view exposes it. No migration of stored data — the graph is reloaded from JSON on every load.

**Testing**: `pytest` (`packages/aoa-action-machine/tests/`, `packages/aoa-maxitor/tests/`, `packages/aoa-demo/tests/`), the client build and typecheck for the Maxitor client, and the closing run `bash scripts/run_checks_with_log.sh`. Verification is adversarial, per `AGENTS.md`: every new test is proved by breaking the code the way it must catch, confirming it fails alone, and restoring.

**Target Platform**: the eight Python packages plus the Maxitor TypeScript client; no adapter surface changes.

**Project Type**: library monorepo — `aoa-action-machine` changes (the types, the DSL, the graph), `aoa-maxitor` changes (store and FSM), `aoa-demo` is migrated, the examples and the docs follow.

**Performance Goals**: no measurable cost. The object is created at import; the graph reads a dict that already exists; no run-time path is added to `transition`/`can_transition`.

**Constraints**: no new dependency; the closing check run must end green; every new module keeps its principle-III header; both public classes get AI-CORE blocks (principle IV); every new symbol gets a one-line docstring (principle V); all text in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 2 new public types, 1 new module, 4 framework modules edited, 1 state-row schema extended, 1 DuckDB table extended, 1 FSM action extended, 1 FSM schema extended, 1 client type and 1 DOT builder extended, 32 demo declarations migrated, 90 state calls and 65 transition calls rewritten, 1 framework test module and its support entities migrated, 2 example directories, 3 documentation pages plus 2 Russian drafts, 1 changelog article.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Eight phases; each becomes a commit only on instruction. Nothing ships on its own initiative. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | The new module, the refusals, the tests and the docs are English. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | `domain/state_vocabulary.py` is new and is written with the full header; the edited modules keep theirs. |
| IV. AI-CORE blocks | Public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `BaseStateEntity` and `StateVocabulary` each get a block; the shape follows `BaseEntity` and `Lifecycle`. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol and every new test gets one. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 6, 7 and 8 are those three steps in that order; no earlier phase absorbs them. The examples are written in the documentation phase, as VI.5 requires, and executed while written. |

**Violations requiring justification**: one, recorded in Complexity Tracking — the string form stays accepted for phases 1–4 and is removed in phase 5, so that every commit on the branch leaves the tree green.

**Re-checked after Phase 1 design**: unchanged. The design added no dependency and no new public name beyond the two the spec names; the client change is one optional field and one colour fallback.

## Project Structure

### Documentation (this feature)

```text
specs/012-lifecycle-state-vocabularies/
├── plan.md              # This file
├── research.md          # Phase 0 — the decisions, the probes and the corpus
├── data-model.md        # Phase 1 — status, vocabulary, state row, FSM payload
├── quickstart.md        # Phase 1 — how to verify by hand
├── contracts/
│   ├── state-declaration-contract.md   # What the vocabulary and the chain accept, and what they refuse
│   └── graph-and-fsm-contract.md       # The state row, the store column and the FSM wire shape
├── evidence/
│   └── scan_lifecycle_calls.py   # the corpus before and after: codes and transition pairs per chain
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── domain/
│   ├── entity.py                       # BaseStateEntity, next to BaseEntity
│   ├── state_vocabulary.py             # NEW — the StateVocabulary mixin, with the full header
│   ├── lifecycle.py                    # entity-accepting DSL, _state_entities, get_state_entity
│   └── __init__.py                     # both names exported
└── graph/
    ├── nodes/state_graph_node.py       # label from the status, attributes from the dump
    └── graph_json_schema.py            # the state row's envelope gains "attributes"

packages/aoa-action-machine/tests/action_machine/
├── domain/
│   ├── test_state_entity.py            # NEW — the object, the vocabulary, the refusals
│   ├── test_lifecycle.py               # migrated to entities; equivalence kept as a test
│   └── ...
├── graph_host/test_lifecycle_graph_node.py   # state row: label, attributes, id, kind
└── support/domain_model/entities.py    # migrated

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/
│   ├── resources/duckdb_graph_resource.py            # state.attributes, the nodes view
│   └── actions/get_lifecycle_finite_automaton_action.py  # read attributes, order, payload
│   └── actions/get_lifecycle_finite_automaton_action_schema.py  # optional attributes per state
├── client/src/
│   ├── model/lifecycleFiniteAutomaton.ts             # attributes?: Record<string, unknown>
│   └── lib/buildLifecycleFsmDotSource.ts             # colour with fallback
└── tests/test_get_lifecycle_finite_automaton_action.py       # label, order, attributes

packages/aoa-demo/src/aoa/demo/model/**/entities/
└── *_lifecycle.py, *cycle*.py          # 32 declarations migrated, codes 1:1

examples/step_22_lifecycle/             # migrated
examples/domain_model/                  # migrated
docs/tutorials/step-22-lifecycle.md (+ ru_draft)
docs/reference/intents-and-invariants.md (+ ru_draft)
docs/CHANGELOG.md                       # one article
```

**Structure Decision**: the types and the DSL live in `aoa-action-machine` (`domain`); the graph description lives where the state row is built (`graph`); the diagram path lives in `aoa-maxitor`; the migration lives in `aoa-demo`. No new layer, no shared helper package, no change to `aoa-langgraph`, the adapters or the OCEL package.

## Phases

Eight phases, one phase — one commit, each leaving the tree green and each proved adversarially before it ends.

1. **The object and the axis class.** `BaseStateEntity` in `entity.py`, `StateVocabulary` as a mixin in a new module with the full header, both exported; the mixin collects the class's status attributes, validates them, exposes `members`/`entity_type`/`by_code`/`codes`, inherits members in a subclass that declares none, and checks that every status in `_template` is a member; the DSL accepts statuses and stores them (`_state_entities`, `get_state_entity`), with overloads for `mypy --strict`. The string form stays accepted for now (see Complexity Tracking). Tests: the object's fields and refusals, the mixin's order/lookup/duplicates/mixed types/inheritance/template check, the equivalence of a template built both ways.
2. **The state row.** `StateGraphPayload` carries the status; `label` from the display name; `properties.attributes` from `model_dump(mode="json")`; `GRAPH_JSON_SCHEMA` widened. Tests: id and kind unchanged, label, all fields present, schema still validates, `Field(exclude=True)` excluded, a non-JSON field refused at build.
3. **Maxitor.** `state.attributes` in DuckDB (both insert paths and the view), `load_states` and the FSM payload, `_STATE_ITEM.attributes`, ordering by `sort_order`, client type and DOT colour with fallback. Tests: attributes round-trip, human label in the payload, order, unchanged DOT with no attributes.
4. **The corpus.** 32 demo declarations migrated (28 chains and 4 sketches), 90 `.state` and 65 `.to` calls rewritten, framework tests and support entities migrated, the two example directories migrated, docstring examples migrated. Evidence: per-chain sets of codes and transition pairs, before and after, identical. Tests: demo suite and examples green on entities.
5. **The removal.** The string branch leaves `state()`/`to()`; the transitional tests are replaced by the refusal tests; a scan proves zero `.state("…"` and `.to("…"` remain in the repository. This is the commit that makes the string form gone, and it is deliberately separate so that phases 1–4 could be reviewed without it.
6. **The check run.** `bash scripts/run_checks_with_log.sh` to zero, the two accepted remarks left alone.
7. **The documentation.** The state-as-object invariant in `docs/reference/intents-and-invariants.md` (FSM section) and the declaration form in `docs/tutorials/step-22-lifecycle.md`, each with its `ru_draft`; a runnable example pair (script + notebook) in `examples/step_22_lifecycle/` showing the vocabulary, the chain, and the state row with its attributes.
8. **The changelog.** One article at the top of `docs/CHANGELOG.md`: statuses became objects with fields; diagrams show human labels and follow the declared order and colour; the string form is gone, with the migration note a user needs.

Phases 6, 7 and 8 **are** the three reserved tail steps of principle VI — check run, documentation, changelog, in that order. `tasks.md` reserves them as exactly three tasks, and no task in phases 1–5 may absorb them. `tasks.md` numbers a read-only baseline as its Phase 1, so plan phase N is tasks Phase N+1.

## Complexity Tracking

| Decision | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| One class per axis (statuses and links in one body) instead of a separate vocabulary class | The maintainer asked for the smallest amount of nesting with a strong link; the axis class needs no binding, generic or decorator, and the template check is structural | A separate vocabulary class gives the same check only with a link — a binding line, a class keyword, `Lifecycle[Vocabulary]` or a decorator — each measured and rejected in research R1 |
| The string form survives until phase 5 | Removing it in phase 1 makes the demo, its tests, the framework tests and the examples fail to import; every commit before the migration would be red, and the branch would be unreviewable | Removing it in phase 1 together with the 32 declarations and ~50 files is one commit that cannot be reviewed as a phase, and a reviewer cannot tell a migration mistake from a design mistake |
| A new module for the vocabulary rather than a class inside `entity.py` | The vocabulary is not an entity and has a different lifecycle of change from the entity base; it also keeps `entity.py` from growing a third subject | Inside `entity.py` it would sit next to `BaseStateEntity` but import the graph opt-out and the naming rules of an entity it is not |
| Exclusion from the model graph is automatic | A forgotten decorator either breaks every graph build (`MissingEntityInfoError`, measured) or doubles the entities; the status type is not a model entity by decision, so the framework enforces it | A per-class decorator is one more line to forget in 32 files, and the failure mode is a broken build, not a visible extra node |
| Attributes are nested under `attributes` rather than spread into `properties` | A status field may be named `state_key` or `lifecycle_class_id`; spreading would let it silently overwrite the row's own fields, and the schema would need a new entry per domain field | Flat properties require a reserved-name list and a schema that changes on every new status attribute |
| The FSM order is initial, then `sort_order`, then key | `initial` first is a drawing invariant, not a status property; `sort_order` is a status property; the key is a stable tiebreak that reproduces today's order when nothing is declared | Sorting only by `sort_order` would let a status with the default `0` jump before the initial state; sorting only by key keeps today's wrong order |
