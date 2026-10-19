---

description: "Task list for #209 — lifecycle states as objects, read by the chain, the graph and the diagrams"
---

# Tasks: Lifecycle states as objects, read by the chain, the graph and the diagrams

**Input**: Design documents from `specs/012-lifecycle-state-vocabularies/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included — the spec's acceptance criteria require them (`SC-003`…`SC-008`) and the repository verifies adversarially (`AGENTS.md`): every test is proved by breaking the code the way it must catch, confirming it fails alone, restoring.

**Organization**: phases follow the plan's commit boundaries, because each phase is one commit and each must leave the tree green. Every task carries the user story it serves (`US1`–`US4`) for traceability. The story order is deliberately not the priority order in two places:

- **US3 (diagrams) lands before US4 (migration)** because the state row and Maxitor read the objects, and the migration is the corpus that exercises them.
- **US2 (refusals) lands after US4** because the string refusal cannot exist until every existing declaration has moved; removing the form earlier would make the demo, its tests and the examples fail to import. The cross-axis check lands early, in Phase 2, with the mixin that owns it.

This ordering is the plan's, not a preference: plan phase 1 → US1, phase 2 → US3 (state row), phase 3 → US3 (Maxitor), phase 4 → US4, phase 5 → US2 (removal), phases 6–8 → the three reserved tail steps.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `US1`–`US4` — the spec's user stories; omitted for the baseline and the tail
- Every task names the file it touches and quotes the constraint it must satisfy

## Path Conventions

- Framework source: `packages/aoa-action-machine/src/aoa/action_machine/`
- Framework tests: `packages/aoa-action-machine/tests/action_machine/`
- Diagram store and FSM: `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/`
- Maxitor client: `packages/aoa-maxitor/client/src/`
- Corpus: `packages/aoa-demo/src/aoa/demo/model/**/entities/`
- Docs and examples: `docs/`, `examples/`
- In this sandbox `uv run` cannot write its cache; `UV_CACHE_DIR=./.uvcache uv run …` is the equivalent of the commands in `quickstart.md`.

---

## Phase 1: Baseline (read-only — no commit)

**Purpose**: record the tree the change starts from, so every later claim has a "before".

- [ ] T001 Capture the corpus "before": write `specs/012-lifecycle-state-vocabularies/evidence/scan_lifecycle_calls.py` that walks `packages/aoa-demo/src` and prints, per lifecycle class, its state codes and `(from, to)` pairs, plus the totals (expect 32 declarations, 90 `.state(`, 65 `.to(` on this tree). Run it and save the output beside it. Also print one current state row and one current FSM state item for `SalesOrderLifecycle` (expect `label == "payment_pending"` and `display_name == "payment_pending"`), which is the "before" the feature corrects. Record the tail of the run for the report.
- [ ] T002 [P] Run the baseline suites and record the result: `UV_CACHE_DIR=./.uvcache uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain packages/aoa-action-machine/tests/action_machine/graph_host packages/aoa-maxitor/tests packages/aoa-demo/tests -q`. This is the green line every phase must return to.

**Checkpoint**: the before-numbers are in hand; nothing has changed.

---

## Phase 2: US1 — a status is an object with fields of its own (Priority: P1) 🎯 MVP

**Goal**: `BaseStateEntity`, the `StateVocabulary` mixin, and an axis class that carries its statuses and its `_template` in one body (`FR-001`…`FR-008`, `FR-016`). The string form is still accepted, for the reason stated in plan Complexity Tracking.

**Independent Test**: an axis class with three statuses carrying a domain field builds the same `StateInfo` entries, initial/final sets and transitions as the string-built twin; `get_state_entity("payment_pending")` returns the object; a status of another axis in `_template` is refused at class definition; a subclass with no statuses inherits them; the status type is not a model-graph entity.

### Implementation for US1

- [ ] T003 [P] [US1] Add `BaseStateEntity(BaseEntity, ABC)` at the end of `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py`, next to `BaseEntity`: `code: str` and `display_name: str`, both required with `Field(description=…)`; a `field_validator` on both refusing `not value.strip()` with `ValueError`; no `model_config` (inherits `frozen=True`, `extra="forbid"`); an `AI-CORE-BEGIN/ROLE/CONTRACT/INVARIANTS/AI-CORE-END` block (principle IV); `__init_subclass__` calling `super()` and then `exclude_graph_model(cls)` so **every** descendant is excluded from the model graph (`FR-002`, `FR-010`, research R3).
- [ ] T004 [P] [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/domain/state_vocabulary.py` with the full principle-III header (path line, title docstring, `═`-ruled sections) and `StateVocabulary` as a **mixin** applied next to `Lifecycle`: `__init_subclass__` collecting `cls.__dict__` values that are `BaseStateEntity` instances **in declaration order**, then validating — a class that declares neither statuses nor its own `_template` inherits `members`/`by_code`/`entity_type` from its parent and skips validation (`FR-003`); otherwise at least one member (`ValueError`), all members sharing one status type (`TypeError`, naming the member and its type), codes unique (`ValueError`, naming the code), and `StateVocabulary` applied to a non-`Lifecycle` class refused (`TypeError`, naming the class); when `_template` is in the same class, every status in it must be one of the members (`TypeError`, naming the status and the class); import `Lifecycle` for the base check (no cycle: `lifecycle.py` does not import this module); the API is **plain methods only** — `members`, `entity_type`, `by_code(code)`, `codes()` — never `__iter__`/`__len__`/`__contains__`, which would leak onto lifecycle instances; an `AI-CORE-BEGIN` block (principle IV); one-line docstrings on every method (principle V). (`FR-003`, `FR-004`, `FR-016`.)
- [ ] T005 [US1] Export both names from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py` (`BaseStateEntity`, `StateVocabulary`) next to `BaseEntity`, and extend that module's `EXAMPLES` docstring with the new declaration form.
- [ ] T006 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py`: add `_state_entities: dict[str, BaseStateEntity]` to the template and to every instance (copied in `__init__` from the template); make `_StateBuilder` carry the status object and register it on `_finalize`; make `Lifecycle.state(key: str | BaseStateEntity, display_name: str | None = None)` take the label from the object and refuse a second label with the object (`TypeError` — the label has one source), keeping the string branch for now; make `.to(*targets)` unwrap a status to `.code`; leave the cross-axis check to the mixin (it reads `_template` in the same class body); add `get_state_entity(key)` and `get_state_entities()`; import `BaseStateEntity` lazily inside the DSL methods, never at module level (`entity.py:119` imports `Lifecycle`, so a module-level import would be a cycle — research R7); add `@overload` signatures for `mypy --strict`; keep every existing validation message and order (`FR-004`…`FR-008`, `FR-016`).
- [ ] T007 [P] [US1] Create `packages/aoa-action-machine/tests/action_machine/domain/test_state_entity.py`: the object's required fields, blank code and blank label refused at construction, immutability, `extra="forbid"`; the vocabulary's declaration order, `by_code`, `codes`, `len`, `contains`, a class with no statuses and no own `_template` inherits its parent's members, a status-only class with no statuses refused, duplicate code refused, mixed status types refused, `StateVocabulary` on a non-`Lifecycle` refused, a status in `_template` that is not a member refused; the status type does not appear in `EntityGraphNodeInspector().get_graph_nodes()` (`FR-002`, `FR-003`, `FR-010`).
- [ ] T008 [US1] Extend `packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle.py`: the equivalence test — a chain built from statuses produces the same `StateInfo` (key, display_name, state_type, transitions) and the same initial/final sets as the string-built twin; `get_state_entity` returns the object and `get_state_entities` the mapping; the same status object classified `final` in one chain and `intermediate` in another builds in both (`FR-005`, `FR-006`); a status of another axis in `_template` refused at class definition, naming the status and the class (`FR-004`); a forward reference to a not-yet-declared status still builds (`FR-004`); and the runtime is unchanged: `current_state` is the code, `transition(code)` returns a new instance of the same class, `can_transition(code)` answers from the template (`FR-007`).
- [ ] T009 [US1] Prove T007/T008 adversarially in `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py` and `.../domain/lifecycle.py`, restoring after each break and confirming the failure is confined to the named test: (a) drop the blank validator → the blank tests fail; (b) drop the duplicate-code check → the duplicate test fails; (c) drop the type guard → the foreign-status test fails; (d) make `exclude_graph_model` inherited rather than per-class → the "not a model entity" test fails; (e) take the label from the code instead of the object → the equivalence test fails; (f) drop the `_template` membership check → the cross-axis test fails; (g) require members on every subclass → the axis-subclass test fails.

**Checkpoint**: US1 is complete; commit 1 is ready on instruction.

---

## Phase 3: US3 — the state row carries the label and the fields (Priority: P3) — commit 2

**Goal**: the graph state row takes its label from the status and carries all declared fields as `properties.attributes` (`FR-009`, `FR-011`).

**Independent Test**: for a chain built from statuses, the state row keeps its id and kind, its `label` is the human label, `properties.attributes` holds every field, a `Field(exclude=True)` field is absent, and the row validates against the schema.

### Implementation for US3

- [ ] T010 [US3] In `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/state_graph_node.py`: add `state_entity: BaseStateEntity | None` to `StateGraphPayload`; resolve the status from the template (`get_state_entity(code)`); set `label` to `display_name` when the status exists and to the key otherwise; add `properties["attributes"] = state_entity.model_dump(mode="json")` when it exists and `{}` otherwise; keep `node_id`, `node_type` and every transition edge exactly as they are (`FR-009`, research R5).
- [ ] T011 [P] [US3] In `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`, `$defs.state.properties`: keep `additionalProperties: false` and the required `lifecycle_class_id` + `state_key`, and add `"attributes": {"type": "object"}` (`contracts/graph-and-fsm-contract.md` §1).
- [ ] T012 [US3] Extend `packages/aoa-action-machine/tests/action_machine/graph_host/test_lifecycle_graph_node.py`: id and kind unchanged against the pre-change row; `label` == display name; `attributes` contains all fields including `code` and `display_name`; an excluded field is absent; the row validates against `GRAPH_JSON_SCHEMA`; a status field that is not JSON-representable makes the node build raise (`FR-009`, `FR-011`, `SC-005`).
- [ ] T013 [US3] Prove T012 adversarially in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/state_graph_node.py` and `.../graph/graph_json_schema.py`: drop `attributes` → the attributes test fails; label from the key → the label test fails; flat properties → the excluded-field and schema tests fail; restore each.

**Checkpoint**: US3's graph half is complete; commit 2 is ready on instruction.

---

## Phase 4: US3 — Maxitor shows labels, order and colour (Priority: P3) — commit 3

**Goal**: the attributes reach the diagram store, the FSM snapshot reports the human label and the declared order, and the drawing uses the declared colour with a fallback (`FR-012`, `FR-013`, `FR-014`).

**Independent Test**: load a graph JSON with attributes; the FSM snapshot's `display_name` is the label, `attributes` is present, the order is initial → `sort_order` → key, and with no attributes the DOT source is byte-identical to today's.

### Implementation for US3

- [ ] T014 [P] [US3] In `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`: add `attributes JSON` to the `state` table, fill it in **both** insert paths (`_fill_table_state` and the by-type insert), and expose it in the `nodes` view with `json_object('attributes', attributes)`; a row without the property yields `{}` (`contracts/graph-and-fsm-contract.md` §2).
- [ ] T015 [US3] In `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action.py`: select `s.attributes` in `load_states`; put it in each state row of the payload; order `states_json` by `(state_type != "initial", attributes.sort_order default 0, key)` (`FR-012`, `FR-013`, data-model §FSM).
- [ ] T016 [P] [US3] In `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action_schema.py`: add optional `"attributes": {"type": "object"}` to `_STATE_ITEM`; change nothing that is required (`FR-012`).
- [ ] T017 [P] [US3] In `packages/aoa-maxitor/client/src/model/lifecycleFiniteAutomaton.ts` add `attributes?: Record<string, unknown>` to `LifecycleFsmStateWire`; in `packages/aoa-maxitor/client/src/lib/buildLifecycleFsmDotSource.ts` use `attributes.color` for the stroke and `attributes.fill_color` for the fill when present, falling back to `paletteForStateType` (`FR-014`, contracts §4).
- [ ] T018 [US3] Extend `packages/aoa-maxitor/tests/test_get_lifecycle_finite_automaton_action.py`: attributes round-trip; `display_name` is the human label (the current test data uses `label == key`, so add a case where they differ); order by `sort_order`; a graph without attributes still loads. Then prove the ordering test adversarially by removing the `sort_order` term (`SC-003`, `SC-004`, `SC-005`).
- [ ] T019 [US3] Build the client from `packages/aoa-maxitor/client/src/model/lifecycleFiniteAutomaton.ts` and `.../client/src/lib/buildLifecycleFsmDotSource.ts`: `cd packages/aoa-maxitor/client && pnpm run typecheck && pnpm run build` (use the package's script names if they differ). Confirm the build succeeds and that the DOT output for a graph without attributes is unchanged.

**Checkpoint**: US3 is complete; commit 3 is ready on instruction.

---

## Phase 5: US4 — the corpus moves without changing a single code (Priority: P4) — commit 4

**Goal**: all 32 declarations use vocabularies, codes and transition pairs kept 1:1, and the framework tests, examples and docstring examples move with them (`FR-015`, `SC-001`, `SC-002`). The string form is still accepted at the end of this phase; Phase 6 removes it.

**Independent Test**: T001's scan, run again, yields the same per-chain code sets and `(from, to)` pairs; the demo suite and the examples run on entities.

### Implementation for US4

- [ ] T020 [US4] Migrate the 28 named chains in the 19 `*_lifecycle.py` files under `packages/aoa-demo/src/aoa/demo/model/**/entities/`: one axis class `class X(Lifecycle, StateVocabulary)` per declaration, with the status type in a module-level `*_state.py` beside it and the statuses as class attributes, one member per existing `.state(...)` call, `code` and `display_name` copied verbatim, `_template` rewritten to `.state(STATUS)` / `.to(STATUS, …)`, classification calls unchanged; `from __future__ import annotations` and the module headers kept (`FR-015`).
- [ ] T021 [US4] Migrate the 4 private cycle-sketch declarations (`analytics/entities/analytics_er_cycle_quad_stub.py`, `catalog/entities/catalog_er_cycle_triangle_stub.py`, `messaging/entities/messaging_er_cycle_triangle_stub.py`, `store/entities/store_er_cycle_ping_pong.py`): same shape, one status each, codes unchanged (`FR-015`; research R8).
- [ ] T022 [US4] Migrate the framework's own call sites: `packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle.py` and any other test module, `packages/aoa-action-machine/tests/support/domain_model/entities.py`, `examples/step_22_lifecycle/`, `examples/domain_model/`, `examples/step_26_maxitor/01_graph.py` and its notebook, and the docstring examples in `lifecycle.py`, `entity.py` and `domain/__init__.py`. The call sites measured on this tree are exactly: `tests/action_machine/domain/test_lifecycle.py`, `tests/action_machine/graph_host/test_lifecycle_graph_node.py`, `tests/support/domain_model/entities.py`, `examples/domain_model/01_domain_model.py` (+ notebook), `examples/step_22_lifecycle/01_lifecycle.py` (+ notebook), `examples/step_26_maxitor/01_graph.py` (+ notebook). The string form still exists, so these may be migrated without a framework change.
- [ ] T023 [US4] Run `specs/012-lifecycle-state-vocabularies/evidence/scan_lifecycle_calls.py` again and diff against T001's output: every chain's code set and `(from, to)` set identical, totals identical. Run `UV_CACHE_DIR=./.uvcache uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain packages/aoa-demo/tests -q` and `UV_CACHE_DIR=./.uvcache uv run python examples/step_22_lifecycle/01_lifecycle.py`, and record both for the report (`SC-001`, `SC-002`).
- [ ] T024 [US4] Prove the 1:1 claim adversarially against `specs/012-lifecycle-state-vocabularies/evidence/scan_lifecycle_calls.py` and the migrated `packages/aoa-demo/src/aoa/demo/model/**/entities/` files: rename one code in one migrated chain → the scan diff reports a changed code set and the corpus test fails; change one `.to(...)` target → the pair diff fails; restore.

**Checkpoint**: US4 is complete; commit 4 is ready on instruction.

---

## Phase 6: US2 — the chain refuses what does not belong to it (Priority: P2) — commit 5

**Goal**: the string form is gone, a string argument is refused with `TypeError`, and the cross-axis refusal written in Phase 2 is covered by a test that has no string path left (`FR-004`, `FR-016`).

**Independent Test**: `.state("new", "New")` and `.to("cancelled")` raise `TypeError`; a status of another axis in `_template` is refused at class definition; no `.state("…"` or `.to("…"` remains anywhere in the repository.

### Implementation for US2

- [ ] T025 [US2] Remove the string branch from `Lifecycle.state` and `_StateBuilder.to` in `packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py`: the parameters become status-only, the overload set collapses to one, the `TypeError` for a non-status names the value and the accepted type; keep every other message and order (`contracts/state-declaration-contract.md` §3).
- [ ] T026 [US2] Replace the transitional string tests with the refusal tests: in `packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle.py`, `.state("new", "New")`, `.to("cancelled")` and `.state(status, "Override")` each raise `TypeError` naming what arrived; add the tests to `test_state_entity.py` if that module owns the vocabulary side (`SC-007`).
- [ ] T027 [US2] Scan the whole repository for leftovers — `.state("`, `.to("` in `packages/`, `examples/`, `tests/`, `docs/`, notebooks — and migrate or remove every real declaration (prose placeholders stay as prose). The scan must report zero call sites outside the refusal tests (`SC-002`).
- [ ] T028 [US2] Prove T026 adversarially in `packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py`: put the string branch back → the `TypeError` tests fail alone; restore. Confirm no other test depends on the string form.

**Checkpoint**: US2 is complete; commit 5 is ready on instruction.

---

## Phase 7: The tail — exactly three steps, in this order (constitution VI) — three commits

> **NOTE**: each of these is its own commit, and no task above may absorb one of them.

- [ ] T029 The check run to zero: walk [quickstart.md](./quickstart.md) steps 1–5 by hand, then run `bash scripts/run_checks_with_log.sh` and fix every remark it reports. The two accepted remarks (the Vite chunk-size advisory and LangGraph's pending deprecation) stay. Three whole-tree checks belong here: (a) the scan finds zero string declarations and zero changed codes (`SC-001`, `SC-002`); (b) the model graph's entity count is unchanged, measured by building the demo graph before and after (`SC-006`); (c) the state rows' ids and kinds are unchanged for every chain, measured by diffing the graph JSON (`FR-009`, `FR-011`, `contracts/graph-and-fsm-contract.md` §1). Paste the tail of the log into the report.
- [ ] T030 The documentation: the state-as-object invariant under the FSM section of `docs/reference/intents-and-invariants.md` — the status carries the label and the fields, the chain keeps the links and the classification, the diagram reads the label — the declaration form in `docs/tutorials/step-22-lifecycle.md`, and the example in `docs/explanation/architectural-constitution.md`, which still shows `.state("new", "New")`; each with its `ru_draft` beside it (gitignored, reported as links). Then the runnable example pair in `examples/step_22_lifecycle/`: a script and a notebook showing the vocabulary, the chain, the state row with `attributes`, and the FSM snapshot with the human label and the declared order; execute both while writing them (constitution VI.5, VI.6).
- [ ] T031 The changelog: one article at the top of `docs/CHANGELOG.md`, dated `2026-10-19`, in the form the existing dated entries use — what a reader can now rely on (statuses are objects with fields; diagrams show human labels and follow the declared order and colour; the string form is gone), with the migration note a user needs and no file list (constitution VI.7).

**Checkpoint**: the change is finished by the repository's own definition.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (baseline)** — no dependency; read-only. T001/T002 can run in parallel.
- **Phase 2 (US1)** — after T001. T003 and T004 touch different files and can run in parallel; T005 after both; T006 after T003; T007 after T004 and T006; T008 after T006; T009 after T007/T008.
- **Phase 3 (US3, state row)** — after Phase 2. T010 and T011 touch different files and can run in parallel; T012 after both; T013 after T012.
- **Phase 4 (US3, Maxitor)** — after Phase 3. T014, T016 and T017 touch different files and can run in parallel; T015 after T014; T018 after T015/T017; T019 after T017.
- **Phase 5 (US4, corpus)** — after Phase 4. T020, T021, T022 touch different trees and can run in parallel; T023 after all three; T024 after T023.
- **Phase 6 (US2, removal)** — after Phase 5, strictly: the string branch must stay until every declaration has moved. T025 → T026 → T027 → T028.
- **Phase 7 (tail)** — T029 → T030 → T031, strictly, after T028.

### Priority inversion, stated

`US2` is P2 and `US3`/`US4` are P3/P4, yet US3 and US4 land first. The reason is mechanical, not a preference: the string refusal cannot be delivered before the corpus stops using strings, and the corpus cannot stop before the objects, the row and the diagrams exist. The cross-axis check does not wait — it is written in Phase 2 with the mixin that owns it.

### Commit boundaries

| Commit | Tasks | What it is |
| --- | --- | --- |
| 1 | T003–T009 | The object, the vocabulary, the entity-accepting DSL, their tests |
| 2 | T010–T013 | The state row: label and attributes |
| 3 | T014–T019 | Maxitor: store, payload, order, colour |
| 4 | T020–T024 | The 32 declarations and the call sites, codes 1:1 |
| 5 | T025–T028 | The string form removed, the refusals |
| 6 | T029 | The check run |
| 7 | T030 | The documentation and the example pair |
| 8 | T031 | The changelog |

Each commit is made only on the maintainer's instruction (constitution I).

### Parallel opportunities

- Phase 1: T001 and T002.
- Phase 2: T003 and T004 (entity.py vs state_vocabulary.py); T007 and T008 after their sources exist.
- Phase 3: T010 and T011 (state_graph_node.py vs graph_json_schema.py).
- Phase 4: T014, T016, T017 (three different files: Python store, Python schema, TypeScript).
- Phase 5: T020, T021, T022 (three different trees) — the largest parallel block.
- Nothing after Phase 5 is parallel: the removal and the tail are sequential by construction.

### Independent test criteria per story

- **US1**: one axis class with three statuses carrying a domain field builds metadata equal to the string-built twin; `get_state_entity` returns the object; a status of another axis is refused; the status type is not a graph entity.
- **US2**: `.state("new", "New")` and `.to("cancelled")` raise `TypeError`; a status of another axis is refused; a repository scan finds no string declaration.
- **US3**: the state row keeps its id and kind, carries the human label and every field; Maxitor's FSM reports the label, the order and the attributes; the DOT is unchanged without attributes.
- **US4**: the per-chain code sets and transition pairs are identical to the baseline; the demo suite and the examples run on entities.

### MVP scope

**US1 alone** (commit 1) is the MVP: a status is an object with fields, the chain takes it, the metadata and the runtime are unchanged, and the equivalence test proves nothing that existed moved. It is demonstrable by a runnable script before the graph knows anything about it.

### Notes

- `[P]` marks different files with no incomplete dependency.
- Verify each test fails before implementing it, and prove it adversarially after.
- Stop at each checkpoint and validate the story on its own before starting the next phase.
- No task writes a commit message, opens a pull request or merges; none of that happens without an explicit instruction in the conversation.
