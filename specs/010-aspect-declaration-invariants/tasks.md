# Tasks: An aspect declaration's signature is an invariant, not a convention

**Input**: Design documents from `specs/010-aspect-declaration-invariants/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: required, not optional. `AGENTS.md` makes verification adversarial — the test is written first, the code is broken the way the test must catch, the test is confirmed to fail alone, the code is restored. Every phase below carries its tests and its adversarial pass.

**Organization**: tasks are grouped by user story so each can be implemented and verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (`US1`…`US5`)
- Every task names the file it writes

## Path Conventions

Repository root is the working directory. Source lives under `packages/aoa-action-machine/src/aoa/action_machine/`, tests under `packages/aoa-action-machine/tests/action_machine/`, evidence under `specs/010-aspect-declaration-invariants/evidence/`.

---

## Phase 1: Setup (baseline evidence)

**Purpose**: capture what the tree does today, so the change can be shown as a before/after rather than asserted.

- [x] T001 Capture the three baseline probes into `specs/010-aspect-declaration-invariants/evidence/baseline.md`: a renamed `@summary_aspect` is accepted, a summary returning `{"not": "a result"}` answers with a `dict`, and `ActionResultTypeError` is raised nowhere in `packages/aoa-action-machine/src` — each with the exact command and its output.
- [x] T002 Re-measure the corpus with the scan at `specs/010-aspect-declaration-invariants/evidence/scan_corpus.py` and write the per-tree table into `specs/010-aspect-declaration-invariants/evidence/corpus-baseline.md`: 763 declarations examined, 499 non-conforming (80 `packages/*.py`, 163 `examples/*.py`, 158 notebook cells, 98 docs snippets), of which 19 are deliberate `pytest.raises` fixtures and 480 are to migrate; plus the list of the 26 `docs/**/*.md` files and 76 notebook files that carry declarations.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the vocabulary every story uses — the two exception classes and the contract table. **No user story can start before this phase is complete.**

- [x] T003 [P] Create `packages/aoa-action-machine/src/aoa/action_machine/exceptions/aspect_signature_error.py` — `AspectSignatureError(SignatureContractError)` with the `# packages/...` path header, an AI-CORE block (`ROLE`/`CONTRACT`/`INVARIANTS`, constitution IV) and the one-line docstring; export it from `packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py` (import plus `__all__` entry).
- [x] T004 [P] Create `packages/aoa-action-machine/src/aoa/action_machine/exceptions/duplicate_summary_aspect_error.py` — `DuplicateSummaryAspectError(TypeError)` mirroring `duplicate_access_decide_error.py`, with an AI-CORE block (`ROLE`/`CONTRACT`/`INVARIANTS`, constitution IV) because it is a new public type; export it from the same `__init__.py`.
- [x] T005 Create `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py` with the `AspectContract` class (fields `kind`, `parameters`, `parameters_with_ctx`, `expected_types`, `return_rule`; AI-CORE block per constitution IV) and the `ASPECT_CONTRACTS` table for all four decorators exactly as in `data-model.md` — `state_after` = `BaseState | None`, `error` = `Exception`, `ctx` = `ContextView`. Validators come in the user-story phases.
- [x] T006 [P] Write `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_contract_table.py` asserting the table's own invariants: every `parameters` starts with `self`; `parameters_with_ctx == parameters + ("ctx",)`; every `expected_types` key exists in `parameters`; the four kinds are present with the orders in `contracts/declaration-contract.md`.

**Checkpoint**: the vocabulary exists, the table is self-consistent, and no behaviour has changed yet.

---

## Phase 3: User Story 1 — A renamed or reordered parameter is refused where the method is written (Priority: P1) 🎯 MVP

**Goal**: all four decorators refuse a signature whose parameters are renamed, reordered, unreachable positionally, or whose trailing `ctx` disagrees with `@context_requires` — while the class body executes.

**Independent Test**: declare a renamed method per decorator and confirm each fails at class creation, with a message naming both orders; `quickstart.md` §1.

### Tests for User Story 1 (write first, confirm they fail)

- [x] T007 [P] [US1] Write `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_names.py` — renamed, reordered, keyword-only, `*args`, and both `ctx`-order cases, for all four decorators; assert the fragments in `contracts/refusals.md` R-1, R-2, R-3.

### Implementation for User Story 1

- [x] T008 [US1] Implement `validate_names`, `validate_positional` and the `ctx`-order hint in `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py`, reusing the message shape of `access_decide_signature.py` (`must declare its parameters as`, `binds by position`).
- [x] T009 [P] [US1] Replace the count-only invariant with `validate_names` + `validate_positional` in `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/summary_aspect_decorator.py`.
- [x] T010 [P] [US1] Same replacement in `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/regular_aspect_decorator.py`.
- [x] T011 [P] [US1] Same replacement in `packages/aoa-action-machine/src/aoa/action_machine/intents/on_error/on_error_decorator.py`.
- [x] T012 [P] [US1] Same replacement in `packages/aoa-action-machine/src/aoa/action_machine/intents/compensate/compensate_decorator.py`.
- [x] T013 [US1] Adversarial pass: disable each validator in turn, confirm exactly the matching test fails, restore, and record the before/after in `specs/010-aspect-declaration-invariants/evidence/adversarial-us1.md`.

**Checkpoint**: a renamed declaration can no longer reach a run. Note that the tree is **not** green yet — 224 `.py` declarations still carry old names and missing annotations; that is US5's work.

---

## Phase 4: User Story 2 — An untyped declaration is refused, and its types are checked at assembly (Priority: P2)

**Goal**: every parameter but `self` and the return carry annotations, refused at declaration; the annotations' types are refused at assembly, with `params` the operation's own, `state` a `BaseState`, `box` a `ToolsBox`, `connections` a `dict[str, BaseResource]`, `ctx` a `ContextView`, `error` an `Exception`, and a compensator's `state_after` a `BaseState | None`.

**Independent Test**: `quickstart.md` §2 — an unannotated method fails at class creation; a `box: str` method fails at `ActionGraphNode(...)`.

### Tests for User Story 2

- [x] T014 [P] [US2] Write `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_types.py` — missing parameter annotation, missing return, unresolvable forward reference, wrong `box`, bare `connections`, wrong `state`, bare `error`, wrong `state_after`; the four return contracts (`-> str` on a regular aspect, `-> dict` on a compensator, `-> Any` and a foreign `Result` on a summary and an on-error handler); the assembly refusal naming the moment it happened (FR-020); `AspectSignatureError` being catchable as `SignatureContractError` and as `TypeError` (FR-021); plus the function-local-operation case (a class declared inside the test function, annotated `-> "ThatAction.Result"`) that must be **accepted**.

### Implementation for User Story 2

- [x] T015 [US2] Implement `validate_annotated` and `validate_types` in `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py`, the latter with the `localns` built from the operation class (research R3), an explicit refusal for annotations that are not classes, and the `return_rule` dispatch for all four kinds: `state_fragment` (`dict[str, Any]`) and `none` here, `operation_result` delegated to the summary and on-error nodes that know the operation's `Result`.
- [x] T016 [P] [US2] Wire `validate_annotated` into `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/summary_aspect_decorator.py`.
- [x] T017 [P] [US2] Wire `validate_annotated` into `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/regular_aspect_decorator.py`.
- [x] T018 [P] [US2] Wire `validate_annotated` into `packages/aoa-action-machine/src/aoa/action_machine/intents/on_error/on_error_decorator.py`.
- [x] T019 [P] [US2] Wire `validate_annotated` into `packages/aoa-action-machine/src/aoa/action_machine/intents/compensate/compensate_decorator.py`.
- [x] T020 [P] [US2] Call `validate_types` for the summary contract in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/summary_aspect_graph_node.py`, before the node is built — parameters and the `Result` return, the latter via the rule completed in T029.
- [x] T021 [P] [US2] Call `validate_types` for the regular contract in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/regular_aspect_graph_node.py`.
- [x] T022 [P] [US2] Call `validate_types` for the on-error contract in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/error_handler_graph_node.py` — parameters, `error: Exception`, and the annotation naming the operation's `Result` (no run-time check of the handler's returned value: that path stays as unchecked as it is today).
- [x] T023 [P] [US2] Call `validate_types` for the compensate contract in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/compensator_graph_node.py`.
- [x] T024 [US2] Adversarial pass: break each type rule (one annotation at a time), confirm the matching test fails alone, restore, record in `evidence/adversarial-us2.md`.

**Checkpoint**: a mistyped declaration is refused before any call is served.

---

## Phase 5: User Story 3 — Two summaries are reported as two summaries (Priority: P2)

**Goal**: an operation declaring two summary aspects is refused at assembly by a purpose-built error naming both methods, instead of dying on an edge with a missing target node.

**Independent Test**: `quickstart.md` §3.

### Tests for User Story 3

- [x] T025 [P] [US3] Write `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_duplicate_summary_aspect.py` — two summaries refused with `DuplicateSummaryAspectError` naming both; the error being catchable as `TypeError` like `DuplicateAccessDecideError` (FR-021); one summary unaffected; no summary still raises `MissingSummaryAspectError`; and the assertion that the message does **not** contain `missing target_node_id`.

### Implementation for User Story 3

- [x] T026 [US3] Raise `DuplicateSummaryAspectError` from `SummaryAspectIntentResolver.resolve_summary_aspects` in `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/summary_aspect_intent_resolver.py`, mirroring `AccessDecideIntentResolver.resolve_check`.
- [x] T027 [US3] Adversarial pass: silence the new refusal, confirm the duplicate test fails (and the old `InvalidGraphError` returns), restore, record in `evidence/adversarial-us3.md`; update the expectation in `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_intent_resolver.py` (currently asserts a list of two).

**Checkpoint**: "no summary" and "two summaries" are two different answers.

---

## Phase 6: User Story 4 — A summary's answer is the operation's Result (Priority: P3)

**Goal**: a summary annotated `-> Any` or with another operation's `Result` is refused at assembly; an instance that is not the operation's `Result` is refused after the method returns.

**Independent Test**: `quickstart.md` §4 — both halves.

### Tests for User Story 4

- [x] T028 [P] [US4] Write `packages/aoa-action-machine/tests/action_machine/runtime/test_summary_answer_contract.py` — assembly: `-> Any` refused, `-> OtherAction.Result` refused, `-> BaseResult` accepted, `-> own Result` accepted; runtime: a mapping, a foreign `Result` and the operation's own `Result`; plus the invariance test that a compliant operation keeps its answer, its event sequence and its log lines.

### Implementation for User Story 4

- [x] T029 [US4] Add the return rule to the summary contract in `aspect_signature.py` (a supertype of the operation's `Result`, `Any` refused) and enforce it from `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/summary_aspect_graph_node.py`.
- [x] T030 [US4] In `packages/aoa-action-machine/src/aoa/action_machine/runtime/aspect_executor.py`, keep the result type `resolve_result_type` already resolves (line 215), compare the returned value with it, and raise `ActionResultTypeError` naming operation, declared `Result` and actual type.
- [x] T031 [US4] Adversarial pass: remove the run-time comparison, confirm the mapping/foreign tests fail and nothing else does; restore; record in `evidence/adversarial-us4.md`.
- [x] T032 [US4] Measure the exit path: 10 000 runs of one compliant operation before and after the change, on this machine, in the same session; record both numbers and their ratio in `evidence/performance.md` — the plan's target is at most 5 % longer, and anything above it is treated as a defect, not as noise.

**Checkpoint**: the documented invariant "must return a typed `Result`" is true at both moments.

---

## Phase 7: User Story 5 — The repository's own corpus complies (Priority: P3)

**Goal**: zero declarations in the repository are refused by the new rules: `packages/`, `examples/*.py`, the example notebooks, and the documentation snippets.

**Independent Test**: `quickstart.md` §5 — every example runs, the scan finds nothing, the check run is green.

### Implementation for User Story 5

- [x] T033 [US5] Migrate the 61 non-conforming declarations under `packages/` (source, `tests/support`, `aoa-demo`, `aoa-maxitor`, `aoa-langgraph`, …) with a throwaway codemod kept outside the repository; review the 19 that the scan marks as asserted refusals and confirm each really is one (a `pytest.raises` fixture stays wrong, with its expected message updated) — anything that is wrong by accident joins the migration; `uv run --extra dev pytest packages/aoa-action-machine/tests/ -v` must pass.
- [x] T034 [US5] Migrate the 163 declarations under `examples/**/*.py`, deriving each summary's `->` from the operation's declared `Result`; execute every example with the repository's environment and confirm it prints what it printed before.
- [x] T035 [US5] Migrate the 158 declarations in the 76 files under `examples/**/*.ipynb`, cell for cell, and confirm each touched notebook's shared cells match its `.py` twin.
- [x] T036 [US5] Re-run the scan over `packages/`, `examples/` and the notebooks and write `evidence/corpus-after.md`: of the 665 declarations in those trees, exactly the 19 deliberate refusals remain non-conforming, each listed with the test that asserts it, and **0 are left to migrate**. The 98 documentation snippets are counted separately and reach the same state in T039, after the documentation step — the scan cannot claim them earlier, and the evidence file says so.
- [x] T037 [US5] Confirm nothing changed for compliant code: `git diff --stat` reviewed by tree, `uv run --extra dev pytest packages/ -v` green for all eight packages, and the refusals outside this feature unchanged (FR-022) — a wrong description, a synchronous method, a wrong suffix and a missing summary still raise exactly the errors they raise today, checked by the existing tests being untouched.

**Checkpoint**: the tree satisfies its own contract.

---

## Phase 8: Polish & Cross-Cutting Concerns — the three reserved tail steps (constitution VI)

**Purpose**: the tail, in this order and as exactly three tasks. No task above absorbs them.

- [x] T038 Run `bash scripts/run_checks_with_log.sh` and fix every remark it reports, to zero; leave the two accepted remarks (Vite chunk size, LangGraph pending-deprecation) untouched; paste the tail of `archive/logs/check-all.txt` into the pull-request description when one is opened.
- [x] T039 Write the documentation: update `docs/reference/intents-and-invariants.md` (the "single summary" and "a correct compensator" sections, plus a section for the declaration contract), the 26 pages listed in `evidence/corpus-baseline.md` that show a declaration, and add the case example `examples/step_01_Action_and_pipeline/05_aspect_declarations.py` with its notebook twin `05_aspect_declarations.ipynb` — every refusal of `contracts/refusals.md` shown as a named case, each executed while written, with its Russian draft beside the English page per the repository's reporting rule; then re-run the corpus scan over `docs/` and append the final line to `evidence/corpus-after.md` — 98 of 98 migrated, which is what closes SC-003.
- [x] T040 Write the changelog as one article in `docs/CHANGELOG.md`: what this work created — four declarations that now say what they receive, a second summary reported as a second summary, and an answer checked against its operation's `Result` — in plain words, with the nuances a user needs, and without a per-file account.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependency; produces the evidence the report needs.
- **Foundational (Phase 2)**: depends on T001–T002 only for context, not for compilation; **blocks every user story**.
- **US1 (Phase 3)**: after Phase 2. No dependency on other stories.
- **US2 (Phase 4)**: after Phase 2, and really after US1 — the same four decorators are edited; T016–T019 depend on T009–T012 having replaced the count check.
- **US3 (Phase 5)**: after Phase 2; independent of US1/US2 in code, but its test file lives beside theirs.
- **US4 (Phase 6)**: after US2 (T029 extends the summary contract and the same node T020 touched) — the runtime half T030 is independent of everything.
- **US5 (Phase 7)**: its `.py` half (T033–T034) is the exception to the phase order — it runs with US1, ahead of US2–US4, because a rule that lands without the corpus turns the suite red (see the MVP note). Its remainder (T035–T037) runs after US1–US4, against the finished rules. **Together they are what makes the tree green**; before T033–T034, the suite fails on the repository's own declarations.
- **Tail (Phase 8)**: after US5. T038 → T039 → T040, in that order and no other (constitution VI).

### Within the stories

- Tests first (T007, T014, T025, T028), confirmed failing.
- Validators in `aspect_signature.py` before wiring them into decorators and nodes.
- Wiring into the four decorators and four nodes is parallel across files.
- Adversarial pass last in each phase, with its evidence file.

### Parallel opportunities

- T003 and T004 (two new exception modules) — different files.
- T005 and T006 (table and its test) — test can be written from `data-model.md` in parallel.
- T009–T012 (four decorators) — four files, no shared edits.
- T016–T019 (four decorators, annotations) and T020–T023 (four nodes) — eight independent files.
- T033, T034, T035 (three corpus trees) — different files; T036 and T037 depend on all three.

---

## How the plan's five phases map onto these eight

The plan is organised by delivery (what ships together); these tasks are organised by user story (who benefits and how it is verified). The two axes cross like this:

| Plan phase | Task phases | Notes |
| --- | --- | --- |
| 1. The contract, its refusals, and the `.py` corpus | Phases 1–6 **plus** T033–T034 | the tasks split phase 1 by story so each refusal is tested on its own; the `.py` migration is the one task pair pulled forward |
| 2. The notebooks | Phase 7, T035 | |
| 3. The check run | Phase 8, T038 | |
| 4. The documentation | Phase 8, T039 | includes the docs snippets and the corpus's last 98 sites |
| 5. The changelog | Phase 8, T040 | |

---

## Parallel Example: User Story 2

```bash
# the four decorators, then the four nodes — eight files, one contract
Task: "Wire validate_annotated into summary_aspect_decorator.py"       # T016
Task: "Wire validate_annotated into regular_aspect_decorator.py"       # T017
Task: "Wire validate_annotated into on_error_decorator.py"             # T018
Task: "Wire validate_annotated into compensate_decorator.py"           # T019
Task: "Call validate_types in summary_aspect_graph_node.py"            # T020
Task: "Call validate_types in regular_aspect_graph_node.py"            # T021
Task: "Call validate_types in error_handler_graph_node.py"             # T022
Task: "Call validate_types in compensator_graph_node.py"               # T023
```

---

## Implementation Strategy

### MVP: US1 plus the migration it forces

US1 alone is the smallest slice that changes behaviour, but it cannot ship alone: once the four decorators refuse renamed parameters, the repository's own 224 `.py` declarations stop compiling. The MVP is therefore **T001–T013 plus T033–T034** — the names rule and the `.py` corpus — and it ends with the suite green and every example script running.

This pulls the `.py` half of US5 **forward**, ahead of US2–US4. That is deliberate and it is the one place the phase order is not the execution order: the migration adds the annotations and returns that US2 and US4 will later require, so nothing is done twice, and the rest of US5 (notebooks T035, scan T036, invariance T037) still runs last. The dependency section below says so explicitly.

### Incremental delivery

1. Phases 1–3 + T033–T034 → renamed declarations refused, corpus compiles → validate with `quickstart.md` §1 and the suite.
2. Phase 4 → untyped and mistyped declarations refused at the right moment → `quickstart.md` §2.
3. Phase 5 → duplicate summary reported properly → `quickstart.md` §3.
4. Phase 6 → the answer checked at both moments → `quickstart.md` §4.
5. T035–T037 → notebooks and the scan at zero → `quickstart.md` §5.
6. Phase 8 → the tail, in the constitution's order.

### Constraints that outrank convenience

- Nothing is committed, pushed or opened as a pull request without the maintainer's instruction in the current conversation.
- Each phase is one commit when instructed; a phase that leaves the tree red is not a phase (hence the pairing in T033–T034).
- The codemod is not committed: its evidence is the diff and the check run.
- A test that passes on both the old and the new code proves nothing; the adversarial passes (T013, T024, T027, T031) are what makes these checks checks.

---

## Notes

- `[P]` marks different files with no dependency on an incomplete task.
- The task IDs are execution order; the story labels are traceability.
- The three tail tasks are not optional and cannot be merged into one another.
- Every new test module opens with its `# tests/...` path line and a `PURPOSE`-sectioned docstring, like `test_access_decide_declaration.py` does (constitution III); a new source module additionally opens with its `# packages/...` path line.
- Nothing in these tasks is committed, pushed or opened as a pull request without the maintainer's instruction in the current conversation (constitution I).
