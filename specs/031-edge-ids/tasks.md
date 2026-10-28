# Tasks: Every Edge of the Graph Gets an Id

**Input**: Design documents from `specs/031-edge-ids/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R8), data-model.md, contracts/edge-identity.md, quickstart.md

**Tests**: Required. Every requirement is testable and the house rule makes verification adversarial — for each new test, break the code the way the test must catch, confirm that test fails and no other does, restore.

**Organization**: one phase = one commit. The code is one commit (Phase 2) because its parts cannot ship apart: an `id` on the edges needs the new schema, and the schema needs the version. Inside Phase 2 the tasks are grouped by user story. The tail — check run, documentation, changelog — is three commits, in that order (constitution VI).

**Issue checkboxes**: issue #285 "Phases" has two: commit 2 → phase 1 (ticked with its sha); commits 3–5 → phase 2 (ticked after commit 5). Commit 1 (design documents) has no issue phase.

**Open review**: `checklists/compatibility.md` is the maintainer's; its unchecked items make `/speckit-implement` stop and ask. T019 and T020 gather the evidence for CHK003, CHK005 and CHK010.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task serves (US1–US4 of spec.md)
- Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every new public class and function carries an AI-CORE block (IV); every class, function and method a one-line docstring ending with a period (V).
- Paths below are relative to `packages/aoa-action-machine/` unless they start with `packages/`, `docs/`, `examples/` or `specs/`.

---

## Phase 1: Setup — design documents (commit 1)

- [ ] T001 Prepare commit 1 with `specs/031-edge-ids/` only (spec, plan, research, data model, contract, quickstart, `checklists/requirements.md`, `checklists/compatibility.md`, tasks; `tasks.ru_draft.md` stays out, `.gitignore` ignores `*_draft.md`): `docs(spec): specify edge ids (#285)`. `.claude/launch.json` is not part of this work and stays out.

---

## Phase 2: Edge ids (commit 2) · US1, US2, US3, US4 — issue phase 1

**Goal**: every exported edge carries an id computed by one public function; the build refuses edges it cannot tell apart; the export is format 1.1 in id order (FR-001 … FR-012).

**Independent Test**: quickstart.md §1–§4 — the demo graph prints `1.1 4841 edges, 4841 distinct ids`, `in id order: True`, `computed == written: True`; the refusal tests pass; gameoffer 0.8.0 → 0.9.0 gives `edges +34 -1 ~9`; Maxitor's answers are unchanged.

### Before the change

- [X] T002 Baseline: confirm `feature/issue-285-edge-ids` is checked out from `feature/issue-273-graph-history` (`4f9c46b5` or later); run `uv run pytest packages/aoa-action-machine/tests packages/aoa-maxitor/tests packages/aoa-demo/tests -q` and record the counts here. Done: from `feature/issue-273-graph-history` at `4f9c46b5` + `f67fe358`; baseline aoa-action-machine 3073 passed, aoa-maxitor 327 passed / 1 skipped, aoa-demo 80 passed (each package run on its own: one run over all three fails to collect because of test-module name clashes, before and after this change).
- [X] T003 [P] Capture the readers' answers before any code changes (SC-005): a script in the session scratch folder (never in the repository) builds the demo graph with `build_registered_interchange_coordinator()` (`packages/aoa-demo/src/aoa/demo/model/interchange_demo_coordinator.py`), saves its `to_json()` as `before.json`, and saves as JSON every answer of Maxitor's diagram actions in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/` for that graph — the full graph, the entity list (ERD), the use case of every domain, the lifecycle of every entity that has one, and the lists of domains, entity kinds and node types. T019 runs the same script again. Done: 227 answers (5 lists and the full graph, 36 use cases, 186 lifecycles) for the demo graph with Maxitor's modules loaded (4917 edges); two runs before the change are identical.

### The rule — US3, US1 (FR-002 … FR-007)

- [X] T004 [P] [US1] Create `src/aoa/action_machine/graph/core/edge_id_rule.py`: `EDGE_SEPARATOR: str = "|"` and `@dataclass(frozen=True) class EdgeIdRule` with `member: str | None = None` ("a property that names the edge in place of its target") and `suffix: str | None = None` ("a property appended to the id"); "At most one of the two is set" — `__post_init__` raises `ValueError` when both are. The module imports nothing from the graph, so the edge classes can import it without a cycle (the table in T006 imports the edge classes). AI-CORE block on `EdgeIdRule`. Done.
- [X] T005 [US1] Declare the rules on their classes (FR-005): in `src/aoa/action_machine/graph/edges/entity_graph_edge.py` `EDGE_TYPE: ClassVar[str] = "entity_relation"` and `ID_RULE: ClassVar[EdgeIdRule] = EdgeIdRule(member="field_name")`; in `src/aoa/action_machine/graph/edges/state_graph_edge.py` `EDGE_TYPE: ClassVar[str] = "lifecycle_transition"` and `ID_RULE: ClassVar[EdgeIdRule] = EdgeIdRule(suffix="from_state")`. Each `__init__` passes `edge_name=self.EDGE_TYPE`; `to_dict` is not touched; each module docstring says in one line how its edges are named. Done.
- [X] T006 [US1] Create `src/aoa/action_machine/graph/edge_identity.py` per contracts/edge-identity.md: re-exports `EDGE_SEPARATOR` and `EdgeIdRule`; `EDGE_ID_RULES: Mapping[str, EdgeIdRule]` = a read-only `MappingProxyType` built from `EntityGraphEdge` and `StateGraphEdge` (`{cls.EDGE_TYPE: cls.ID_RULE}`); `edge_id(row: Mapping[str, Any]) -> str` reads `source_id`, `type`, `target_id` (each a non-empty string) and ignores any `id` in the row; a `member` rule puts `properties[member]` in place of `target_id`; a `suffix` rule appends `|properties[suffix]`; raises `ValueError` naming the type and the field when a required key or the rule's property is "missing, empty or not a string", or when any part contains `|`. AI-CORE on `edge_id` (`ROLE`, `CONTRACT`, `INVARIANTS` — pure, `FAILURES`). Then, in fresh interpreters, `uv run python -c "import aoa.action_machine.graph.edge_identity"` and `uv run python -c "import aoa.action_machine.graph.core.node_graph_coordinator"` both succeed. Done; both imports succeed in fresh interpreters.
- [X] T007 [P] [US3] Tests of the function in `tests/action_machine/graph/test_edge_identity.py`: the default id (a `@check_roles` row as in data-model.md); `entity_relation` named by `field_name`, and two rows that differ only in `target_id` give one id; `lifecycle_transition` ends with `|<from_state>`, and two rows into one state from `draft` and `paused` give two ids; a row without `id` (format 1.0), the same row with the right `id` and the same row with a wrong `id` give one id; a row without `source_id`, `type` or `target_id` raises `ValueError` naming it; `entity_relation` with `field_name` missing, `""` or `5` raises `ValueError` naming `entity_relation` and `field_name`, and the same three for `lifecycle_transition` and `from_state`; `|` in the source, the target, `field_name` or `from_state` raises `ValueError`; `EdgeIdRule(member="a", suffix="b")` raises `ValueError`. Done: 22 cases in `test_edge_identity.py`.
- [X] T008 [P] [US1] Guard test in `tests/action_machine/graph/test_edge_identity.py`: import every module under `aoa.action_machine` (`pkgutil.walk_packages`), collect every `BaseGraphEdge` subclass that has `ID_RULE` in its own `__dict__`; each is in `EDGE_ID_RULES` under its `EDGE_TYPE` with the same rule, and the table holds nothing else. Done: `test_every_declared_rule_is_in_the_table`.
- [X] T009 [US1] Adversarial check of T007–T008, one break at a time: drop `entity_relation` from the table → only the relation tests fail; return `row["id"]` when present → only the wrong-`id` test fails; accept an empty `from_state` → only that refusal fails; declare an `ID_RULE` on a third edge class without adding it to the table → only the guard fails. Restore; record here. Done: (a) table without `entity_relation` → the relation tests and the guard fail, and every graph with repeating relations is refused at build (17 tests + the 2 demo tests) — the refusal of US2 doing its job; (b) a written `id` returned → only `test_an_id_already_in_the_row_is_ignored`; (c) an empty `from_state` accepted → only `test_a_row_without_its_rule_property_is_refused`; (d) a rule on a third class → only the guard. Restored.

### The build refuses — US2 (FR-008, FR-009)

- [X] T010 [P] [US2] In `src/aoa/action_machine/graph/core/exceptions.py`, next to `DuplicateNodeError`: `DuplicateEdgeError(ValueError)` with `edge_id`, `first`, `second` on the instance; each side described as `<source_id> -[<type>]-> <target_id>` plus the property its rule uses (for example `field_name=offers`); `str()` names the id and both sides. AI-CORE block (`ROLE`, `CONTRACT`, `INVARIANTS`, `FAILURES`); the module's exceptions diagram gains the branch; export it wherever `DuplicateNodeError` is exported. Done; `DuplicateNodeError` is exported from no package `__init__`, so neither is `DuplicateEdgeError`.
- [X] T011 [US2] In `src/aoa/action_machine/graph/core/node_graph_coordinator.py`: a new pass `_validate_edge_identity`, called in `build()` right after `_single_pass_validate_and_wire`: every node id containing `|` → `InvalidGraphError` naming the node (every node, not only those with edges — research R3); for every edge, its row from `to_dict(source_id=…)` and `edge_id(row)`; a `ValueError` from it → `InvalidGraphError` naming the edge and the property; an id already seen → `DuplicateEdgeError`. The docstring of `build()` lists the new refusals. Done.
- [X] T012 [P] [US2] Tests in `tests/action_machine/graph/test_edge_identity.py`, with a harness like `_HarnessInspector` in `tests/action_machine/graph/test_node_graph_coordinator_json.py`: two edges of one type without a rule between the same two nodes → `DuplicateEdgeError`, whose message holds the id and both edges; a node with no edges whose id contains `|` → `InvalidGraphError` naming the node; a `StateGraphEdge` with `from_state="dr|aft"` → `InvalidGraphError` naming the edge and `from_state`; a harness graph with none of these builds; the demo graph builds. Done: four build tests in `test_edge_identity.py` (two plain `AssociationGraphEdge`s for the duplicate; edges with properties need their own `to_dict`).
- [X] T013 [US2] Adversarial check of T012, one break at a time: remove the duplicate check → only the duplicate test fails; check only the node ids that edges use → only the node test fails; skip the edge rows → only the `from_state` test fails. Restore; record here. Done: (e) no duplicate check → only the duplicate test; (f) no node id check → only the node test; (g) an edge without a valid id skipped → only the `from_state` test. Restored.

### The export — US1, US4 (FR-001, FR-010, FR-011)

- [X] T014 [US1] In `NodeGraphCoordinator.to_json()`: after each edge's `to_dict`, `row["id"] = edge_id(row)`; edges sorted by `id`; `schema_version` `"1.1"`; the module docstring says edges carry `id` and come in id order. `_build_indexes` and the in-memory order stay as they are (research R6). Done.
- [X] T015 [US4] In `src/aoa/action_machine/graph/graph_json_schema.json` (read by `graph_json_schema.py`): `schema_version` `"1.1"`; `link_row` gains `id` — `{"type": "string", "minLength": 1}`, required; `additionalProperties: false` kept. Docstrings in `graph_json_schema.py` that name `1.0` say `1.1`. Done; `graph_json_schema.py` names no version, nothing to change there.
- [X] T016 [US4] Move the tests that write `"1.0"` payloads for the schema to `"1.1"` and give their hand-made edges an `id` (payloads made by `to_json()` need nothing): `tests/action_machine/graph/test_depends_graph_edge_mode.py`, `test_entity_field_graph.py`, `test_entity_reference_graph.py`, `test_graph_json_schema_entity_kind.py`, `test_graph_json_schema_generalization.py`, `test_graph_json_schema_specialization.py`, `test_graph_json_schema_values.py`, `test_node_graph_coordinator_json.py`, and `tests/action_machine/graph_host/test_lifecycle_graph_node.py`. Maxitor's tests are not touched (FR-012). Done: nine files; hand-made edges get `edge_id(edge)`, the depends fixture a literal `a|@depends|b`.
- [X] T017 [P] [US1] Tests in `tests/action_machine/graph/test_node_graph_coordinator_json.py`: on the demo graph — every edge has an `id`, no id repeats, every `(source_id, type, target_id)` pair that repeats gets different ids (SC-001; assert the properties, record the counts — 4841 edges, 61 pairs — here, do not hard-code them); for every edge `edge_id` of the row without `id` equals its `id` (SC-002); edges in id order; `schema_version == "1.1"`; two exports of one build and of two builds are equal strings (SC-004); the export validates against `GRAPH_JSON_SCHEMA`, and the same export with one edge's `id` removed does not. With small entities declared in the test module: two builds that differ only in a relation's target entity give that relation one id; two that differ only in a field's position give its `entity_field` edge one id (US1 scenarios 4–5). Done: in `test_node_graph_coordinator_json.py` on the graph of everything loaded (`create_node_graph_coordinator()`, since the action-machine tests do not load the demo) — id on every edge, unique, id order, 1.1, computed == written, two builds equal, schema refuses a missing `id`, a retargeted relation and a relation with changed properties keep their id; the demo graph's own test is `packages/aoa-demo/tests/model/test_demo_edge_ids.py` — no id repeats, every repeating pair gets distinct ids, only `entity_relation` and `lifecycle_transition` repeat, computed == written. Counts: 4841 edges, 61 repeating pairs (2 + 59).
- [X] T018 [US1] Adversarial check of T014–T017, one break at a time: sort by `(source_id, type, target_id)` again → only the order test fails; write `"1.0"` → only the version tests fail; drop `id` from the schema's `required` → only the missing-`id` test fails; name a relation by `target_id` + `field_name` → only the retarget test fails. Restore; record here. Done: (h) the old order → only the order test; (i) `1.0` written → the three round-trip tests, the order/version test and the two tests that validate an export against the schema (const `1.1`); (j) `id` not required → only `test_the_schema_requires_an_edge_id`; (k) relation named by target + field → only the two relation tests. Restored.

### The readers and the hand check — FR-012, SC-003, SC-005

- [X] T019 [US1] Run `uv run pytest packages/aoa-maxitor/tests -q` — green with no test changed; run T003's script again and compare every answer with the saved one — identical, including the order of rows and every coordinate an answer carries. A difference is a finding to resolve before the commit (compatibility CHK003, CHK005); record the result here. Done: Maxitor 327 passed / 1 skipped, no test changed; all 227 answers byte-identical before and after, although 4641 of 4917 edges changed position in the file and nodes are identical (evidence for compatibility CHK003, CHK005).
- [X] T020 [US3] Hand check of SC-003 (quickstart.md §3) on gameoffer's snapshots 005 and 006 in the session scratch folder: `edges +34 -1 ~9`. Also compute `edge_id` for every edge of snapshots 001–006 — none may raise (compatibility CHK010). Record both here for the pull request; the files are not committed. Done: 005 → 006 gives `edges +34 -1 ~9`. All six snapshots (001–006, 416–550 edges, format 1.0) compute ids without an error and none has two edges with one id (evidence for compatibility CHK008, CHK010).
- [X] T021 Full suites green against T002's baseline (`uv run pytest packages/aoa-action-machine/tests packages/aoa-maxitor/tests packages/aoa-demo/tests -q`); quickstart.md §1 prints what it expects. Prepare commit 2: `feat(graph): every edge of the graph gets an id (#285)`. Tick issue phase 1 with its sha (`gh issue edit 285`). Done: three suites green (3102 / 327 + 1 skipped / 82), quickstart §1 as expected; committed as commit 2, issue phase 1 ticked.

---

## Phase 3: The check run (commit 3)

- [X] T022 Run `bash scripts/run_checks_with_log.sh` and take it to zero — only the two accepted remarks stay (the Vite chunk-size advisory, LangGraph's pending-deprecation warning); prepare commit 3: `chore: take the check run to zero (#285)`. If the first run is already clean there is nothing to commit; record that here. Done: the first run on `50396ef1` is clean — 37 steps OK (ruff, mypy on 892 files, pylint 10.00/10, vulture, radon, wheels, every package's tests: action-machine 3102, Maxitor 327 + 1 skipped, demo 82, client 223), only the two accepted remarks (Vite chunk size, LangGraph pending deprecation); nothing to commit.

---

## Phase 4: Documentation (commit 4)

- [X] T023 A new section of `docs/tutorials/step-26-maxitor.md`, after "It's the same graph the machine builds": how an edge is named by default; a relation named by its field, which keeps its id when it points at another entity; a lifecycle transition with the state it leaves; the two refusals; computing ids for a file of format 1.0; what format 1.1 changes for a reader (the `id` field, the id order, the version, the stricter schema). Every case runnable in `examples/step_26_maxitor/11_edge_ids.py` and its executed notebook `examples/step_26_maxitor/11_edge_ids.ipynb`; the Russian draft beside the page (`docs/tutorials/step-26-maxitor.ru_draft.md`, not committed). Prepare commit 4: `docs(graph): edge ids, with runnable examples (#285)`. Done: the section "Every edge has an id" after "It's the same graph the machine builds"; `11_edge_ids.py` shows seven cases on the demo graph (default rule, relation by field and retarget, transition by the state it leaves, both refusals, a 1.0 file, what 1.1 changes) with its real output in the docstring; the notebook has 19 cells, executed, and its output equals the script's; the Russian section appended to `step-26-maxitor.ru_draft.md`.

---

## Phase 5: Changelog (commit 5)

- [ ] T024 One article at the top of `docs/CHANGELOG.md` about what this work gives: the edges of a graph have names, so two versions can be compared edge by edge, and what changes for whoever reads graph files (format 1.1, files of 1.0 still readable) — plain words, no technical detail, no per-file account (constitution VI); its Russian version in `docs/CHANGELOG.ru_draft.md`. Prepare commit 5: `docs(changelog): every edge of the graph has a name (#285)`. Tick issue phase 2.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 next; inside it: T002–T003 before any code change; T004 → T005 → T006 (the rule type, then the classes, then the table); T010 and T011 need T006; T014 needs T011 (the build guarantees the ids it writes are unique); T015–T016 go with T014; T019–T021 last.
- Phases 3 → 4 → 5 strictly last, in this order (constitution VI).
- No commit, push or pull request without the maintainer's word in the conversation (constitution I).

## Parallel Opportunities

- T003 beside T004.
- T007 and T008 (one test file, independent tests) beside T010.
- T012 beside T014–T015 once T011 is done.
- T017 beside T016.

## Implementation Strategy

- The whole of Phase 2 is the result: the ids, the refusals and the export ship together, as one commit, or not at all.
- Then the tail — check run, documentation, changelog — closes #285. The next step of #273 (#286, the graph file) starts from this branch's merge into `feature/issue-273-graph-history`. Publishing to PyPI and updating servers are not part of it.
