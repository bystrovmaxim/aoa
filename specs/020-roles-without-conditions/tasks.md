# Tasks: Roles Without Conditions

**Branch**: `feature/issue-248-check-roles-without-grant-guard`
**Date**: 2026-10-24
**Input**: [Plan](plan.md), [specification](spec.md), [research](research.md), [data model](data-model.md), [validation guide](quickstart.md), and the [declaration](contracts/role-declaration.md), [answers](contracts/decision-and-cascade.md) and [graph](contracts/graph-projection.md) contracts.
**Tests**: Required — the specification's acceptance scenarios, SC-003 and FR-018 all rest on them. Each procedure pins its own contract by test or by recorded search before the next one depends on it.
**State**: Tasks generated only. Every checkbox is unchecked; nothing here is implementation acceptance.

## Execution rules and path conventions

Paths are repository-relative. Preserve the current working tree and staging; never commit, push, open a pull request or merge without a separate explicit instruction; never change branches and never edit `.specify/memory/constitution.md`.

The procedures below are workflow groupings, not commit phases. Any later authorized commit follows the project's one-phase/one-commit rule.

**Why the surgery is one foundational step.** The removed mechanism spans a decorator, a resolver, the role checker, the cascade and two graph classes: the package stops importing if any one of them is edited alone. Procedure 2 therefore performs the removal as one coherent change, and each story procedure afterwards pins its own slice — its tests, its adversarial mutation, its recorded evidence — with a mutation that disables the branch under test, which is the adversarial discipline the constitution asks for rather than a decorative red-first step.

`[P]` marks tasks in the same ready batch that touch distinct files and have no incomplete dependency within that batch. Tasks without `[P]` that touch the same production module stay sequential.

Two boundary notes:
- `packages/*/CHANGELOG.md` files are history and are not rewritten. Only `docs/CHANGELOG.md` receives the new article, in T029.
- Issue #247's code-isolation check is **not in the tree** — `graph/validators/` holds only entity validators (four of them since #262: field, inverse, specialization and the #261 role-compatibility validator). T025 records that mutation as a review with a recorded search and says so in its result, per FR-018.

## Procedure 1 — Setup and baseline evidence

**Purpose**: Know what the tree does today on a clean base. The branch now equals `main` (`90dd83e5`): the `relation_containers.py` / `entity_field_validator.py` changes are committed as part of #262, the working tree is clean, and #262 added a fourth entity validator plus the `specs/021-*` planning set. T001 records that base, and T002 re-derives the migration inventory from it.

- [x] T001 Run the baseline one package at a time, the way `scripts/run_checks_with_log.sh` does — `uv run --extra dev pytest packages/aoa-action-machine/tests/ -q`, then the same for `aoa-demo` and `aoa-maxitor` (a single combined invocation breaks Maxitor's `tests.*` import mode) — and record the actual result — collected, passed, failed, skipped, plus the full list of collection-error files — in `specs/020-roles-without-conditions/evidence/baseline.md`; state the exact commit (`git rev-parse HEAD`), and note whether the tree is clean or carries uncommitted Procedure 2 changes, so a later failure is attributable to the change rather than to a pre-existing modification. Note in the same file that the other five packages are covered by T029 and are not baselined here because nothing in this change reaches them.
- [x] T002 Re-confirm the migration inventory named in [research.md](research.md#r12--teaching-material) and [R13](research.md#r13--test-migration-shape) against the current tree, and write the result to `specs/020-roles-without-conditions/evidence/inventory.md`: the 17 test modules, the 3 demo actions, the 6 example scripts and their 6 notebooks, the 3 documentation pages, and the 4 modules that disappear. A file that has appeared or vanished since the research is recorded, not silently absorbed.
- [x] T003 Write `specs/020-roles-without-conditions/evidence/mutations.md` with the five mutations of FR-018 as a repeatable recipe for a temporary copy (`git worktree` or `cp -R` into `archive/`): what to edit, which command must fail, which neighbouring control must still pass. No mutation is applied to the user's working tree.

## Procedure 2 — Foundational: the mechanism leaves the tree

**Purpose**: Delete the condition half of `@check_roles` and keep the package importing. Complete T004–T010 before any story procedure.

- [x] T004 Rewrite `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_decorator.py`: one normalization path (one or more role arguments, or one tuple/list; sentinels allowed anywhere; every member a `BaseRole` subclass), `_role_info = {"spec": ...}` as the only storage, `UNUSED` still refused and `DEPRECATED` still warned, and the signature `check_roles(*specs, **unsupported)` whose refusal carries the migration sentence from [the declaration contract](contracts/role-declaration.md#refused-forms). Delete `_normalize_grants`, `_spec_from_grants`, `_grants_for_normalized_spec` and `_reject_async_condition`.
- [x] T005 [P] Rewrite `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/roles.py` around the single spec: dense alternatives in declaration order, `GuestRole` present ⇒ `None`, otherwise `AnyRole` present ⇒ answer for at least one active role, otherwise `issubclass` over the caller's non-silenced roles; `Refused(gate=Gate.CHECK_ROLES)` when nothing matches. Delete `_spec_from_grants`, `_sentinel_answer`, `_concrete_answer`, `_denial_answer` and the `role_matched`/`refused_reason` bookkeeping; keep `_active_user_roles` and the `MissingCheckRolesError` path.
- [x] T006 [P] Update `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/role_graph_edge.py` to build from a role class alone (`properties={}`, same exported `to_dict`), and `get_role_edges` to read the spec and deduplicate by identity in declaration order. Update `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/action_graph_node.py` to drop `guard` and `guard_reason` from `properties` and from its AI-CORE block, and `role_graph_node.py` to drop the paragraph that explains where conditions live.
- [x] T007 [P] Delete `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py` and remove `Grant`/`grant` from `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/__init__.py`, including its `__all__` entries and the docstring text that names them.
- [x] T008 Delete `packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py`,
  `packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_condition_async_error.py` and
  `packages/aoa-action-machine/src/aoa/action_machine/exceptions/condition_reason_error.py`; remove their imports and `__all__` entries from `.../intents/check_roles/__init__.py` and `.../exceptions/__init__.py`; delete `resolve_grants`, `resolve_guard` and `resolve_guard_reason` from `.../intents/check_roles/check_roles_intent_resolver.py` and rewrite its AI-CORE block. Delete the two test modules whose only subject went with them — `packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_reason_validation.py` and `packages/aoa-action-machine/tests/action_machine/exceptions/test_access_condition_async_error.py` — and confirm nothing else imports them.
- [x] T009 [P] Rewrite `packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/gate.py` with exactly three members and a header stating three, and `.../access_control/cascade.py` without `guard_answer`/`guard_gate`, with `GATES_BEFORE_RUN = (Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES)`, the two `__all__` and `_STEPS` entries gone, and the header stating three ordered steps and three answers.
- [x] T010 Sweep the remaining prose of the mechanism: `.../intents/access_control/undecided.py` (the `Gate.GUARD` example), `.../intents/access_control/refused.py`, `.../intents/access_control/__init__.py` (the five-word list), `.../exceptions/authorization_error.py` (level `2`), `.../intents/check_roles/check_roles_intent.py`, and `.../model/base_action.py` (the `@check_roles`/`guard=` sentence). Include any test docstring, comment or printed line that states "four steps" or "five words", so no count outlives the vocabulary. Every touched module keeps its path header and its `PURPOSE` section.

## Procedure 3 — US1: a declaration of who may call, and nothing else (P1)

**Goal**: the accepted forms, the refusals, the migration message and the match semantics are pinned by tests.
**Independent acceptance**: an operation declared with each accepted form builds and answers as [the declaration contract](contracts/role-declaration.md) says, and each refused form fails where it is written with a message naming the replacement.

- [ ] T011 [P] [US1] Extend `packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_check_roles_class_roles.py` with one named case per accepted form (bare role, several positional roles, tuple, `GuestRole`, `AnyRole`, `GuestRole` beside a role, `AnyRole` beside a role, the same role twice) and per refused form (no argument, string, empty tuple, empty list, non-role object, `guard=`, `guard_reason=`, `when=`, an unknown keyword). Assert the exception type and that the migration text contains `@access_decide`; assert that a duplicate declaration yields the same spec as the single role.
- [ ] T012 [P] [US1] Replace `packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_check_roles_grant.py` with `test_check_roles_removed_mechanism.py`: `from aoa.action_machine.intents.check_roles import grant` raises `ImportError`; the same for `Grant`; `getattr` on the module returns nothing; `RoleSpecTypeError` is raised at class definition for the three removed keywords with the replacement sentence; `ConditionReasonError` and `AccessConditionAsyncError` are absent from `aoa.action_machine.exceptions`.
- [ ] T013 [US1] Extend `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py` with the matching contract: `GuestRole` beside a role allows a caller with no roles; `AnyRole` beside a role requires at least one non-silenced role; a silenced caller role grants nothing; `UNUSED` still refused where declared; `DEPRECATED` still warns; an operation with no `@check_roles` still raises `MissingCheckRolesError`. Delete the two cases whose subject was `grant(GuestRole, when=...)` and `grant(AnyRole, when=...)`.
- [ ] T014 [US1] Run mutation 1 and mutation 2 of `evidence/mutations.md` in a temporary copy — re-add `@check_roles(grant(Role))`, and remove `@check_roles` from an operation — and record in `specs/020-roles-without-conditions/evidence/mutations.md` that T012's and T013's assertions fail respectively while their neighbouring controls pass; restore the copy.

## Procedure 4 — US2: the object rule holds what the declaration cannot say (P1)

**Goal**: the conditions that used to be declarative live in `@access_decide`, answer on both paths, and never repeat the role check.
**Independent acceptance**: a locked object and a foreign object both refuse with `ACCESS_DECIDE` on `machine.run` and on `machine.check_access_decide`, and a search finds no object rule repeating its own declared role check.

- [ ] T015 [P] [US2] Extend `packages/aoa-action-machine/tests/action_machine/runtime/test_action_product_machine_check_access_decide.py` and `.../runtime/test_machine_decisions.py` with the migrated shape: a reason-bearing `Refused("REASON")`, the shared `FORBIDDEN_OBJECT`, the same answer from both entry points, a wrong return type (`bool`, `None`, a string) and a raising rule both yielding `Undecided` with gate `ACCESS_DECIDE` and never `Allowed`.
- [ ] T016 [P] [US2] Extend `packages/aoa-action-machine/tests/action_machine/intents/access_decide/test_access_decide_context.py` with a rule that declares `user.roles` beside `user.user_id`, reads both through the view, and refuses for a reason the declaration alone cannot express; assert the undeclared key still raises `ContextAccessError`.
- [ ] T017 [US2] Record the FR-008 review in `specs/020-roles-without-conditions/evidence/role-check-search.md`: run a scoped search over the migrated actions and examples for `issubclass(`, `RoleMode` and role-helper calls inside `@access_decide` bodies, list every hit with its verdict, and state in one line that no object rule repeats the check its own declaration performs.

## Procedure 5 — US3: three words, three steps (P1)

**Goal**: the published vocabulary is three words, the order has two pre-run steps, and a stored removed word is refused.
**Independent acceptance**: every answer produced anywhere carries one of the three words, `Refused(gate="WHEN")` fails validation, and the pre-run phase is two steps.

- [ ] T018 [P] [US3] Extend `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_verdict.py` and `.../exceptions/test_access_denied.py`, `.../exceptions/test_access_undecided.py`: `len(Gate) == 3`; `Refused(gate="WHEN")`, `Refused(gate="GUARD")`, `Undecided(gate="WHEN", cause=ValueError())` and the same through `model_validate` from stored data all fail validation; no answer anywhere carries a removed word.
- [ ] T019 [P] [US3] Extend `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_gate_order.py`, `.../test_cascade.py` and `.../test_cascade_decide.py`: `GATES_BEFORE_RUN` is the two named steps and `GATES_AT_OBJECT` the third; the first answer wins; a step that raises yields `Undecided` naming its own word with the cause kept private; `guard_gate` and `guard_answer` no longer exist in the module.
- [ ] T020 [P] [US3] Update `packages/aoa-action-machine/tests/action_machine/runtime/test_access_events.py` and `.../graph/test_declared_reasons.py`: delete the cases whose subject was a condition's refusal word, keep the event and reason cases that still apply, assert the decision event carries one of the three words, and assert the consequence FR-017 describes — an object rule that refuses publishes the run's start before the refusal, so the sequence is visible in the events rather than a refusal that precedes the run.
- [ ] T021 [US3] Run mutations 3 and 4 of `evidence/mutations.md` in a temporary copy — a silenced caller role required by an operation, and an object rule added to a `GuestRole` operation that allowed — and record that the role gate still refuses the first and the second now refuses, with controls passing.

## Procedure 6 — US4: the graph says roles, and points at the rule (P2)

**Goal**: the graph carries no condition data, one edge per distinct role, and the `AccessDecide` node as its only statement about an object rule.
**Independent acceptance**: an exported graph has no `when`/`when_reason`/`guard`/`guard_reason` anywhere, one edge per distinct role, and an `AccessDecide` node exactly when a rule is declared.

- [ ] T022 [P] [US4] Extend `packages/aoa-action-machine/tests/action_machine/graph/edges/test_role_graph_edge.py`: one edge per distinct role in declaration order, duplicates collapsed, exported `properties == {}`, no callable reachable on the edge.
- [ ] T023 [P] [US4] Extend `packages/aoa-action-machine/tests/action_machine/graph/nodes/test_action_graph_node.py`: the action node carries no `guard`/`guard_reason`, the `AccessDecide` node appears exactly when the operation declares one, and its required-context companions name the declared keys.
- [ ] T024 [US4] Run `uv run --extra dev pytest packages/aoa-maxitor/tests/test_duckdb_access_decide_type.py packages/aoa-maxitor/tests/test_full_graph_payload_metrics.py -q` unchanged and record in `specs/020-roles-without-conditions/evidence/maxitor.md` that the payload still validates and the `AccessDecide` node still reaches DuckDB; no Maxitor source is edited.

## Procedure 7 — US5: the repository's own declarations (P2)

**Goal**: the demo and the teaching pages use the new mechanism, and nothing in the tree imports a removed name.
**Independent acceptance**: the demo's three actions and both test modules pass; the six example scripts and their notebooks run and print what the page records.

- [ ] T025 [P] [US5] Migrate `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/actions/cancel_order.py` to `@check_roles(CustomerRole)` plus `cancel_order_access_decide` (locked ⇒ `Refused("ORDER_LOCKED")`, another customer's order ⇒ `FORBIDDEN_OBJECT`), and update `packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py` to assert both refusals with gate `ACCESS_DECIDE`. Record in `evidence/mutations.md` that the fifth mutation — a module-level read inside the object rule — is verified here by review and search, not by a check, because #247 is not in the tree.
- [ ] T026 [P] [US5] Replace the two shape actions: `when_refusal_shape_action.py` → `object_rule_refusal_shape_action.py` (`ObjectRuleRefusalShapeAction`, the author's own reason) and `guard_refusal_shape_action.py` → `forbidden_object_shape_action.py` (`ForbiddenObjectShapeAction`, the shared refusal for every caller), each with its path header, `PURPOSE` and one-line docstrings; update `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/__init__.py` and `packages/aoa-demo/tests/model/test_access_cascade_shapes.py` to the new names and to "no condition on the edge or the node".
- [ ] T027 [US5] Rewrite the six scripts under `examples/step_03_authorization_and_roles/`: `02_grant.py` → `02_object_rule.py`, `03_guard.py` → `03_shared_object_rule.py`, `17_grant_fallback.py` → `17_branch_order.py`, `22_reason_required.py` → `22_reason_in_branch.py`, plus `07_three_answers.py` and `13_cascade.py` rewritten in place for three words. Each keeps `main()`, its `# %%` sections and its printed narrative; each is executed and its actual output captured.
- [ ] T028 [US5] Regenerate the six notebooks beside those scripts from the same steps, so script and notebook show identical cells and identical output; execute each notebook end to end and record the run in `specs/020-roles-without-conditions/evidence/examples.md`.

## Procedure 8 — Closing: check run, documentation, changelog

Exactly three tasks, in this order. No earlier task may absorb them, and none of them may be skipped or reordered.

- [ ] T029 Run `bash scripts/run_checks_with_log.sh` and take it to zero: Ruff `--fix`, Ruff lint, mypy across all eight packages, pylint, vulture, the package-boundary and metadata checks, the wheel/sdist build and packaging smoke, Radon, the Maxitor samples check and the test suite of every package including `aoa-demo`. Fix every remark; the only survivors are the two the constitution names (the Vite chunk-size advisory and LangGraph's pending-deprecation warning). Record the tail and the exit status in `specs/020-roles-without-conditions/evidence/check-run.md`.
- [ ] T030 Write the documentation after the code is settled: the tutorial's condition sections and its migration section in `docs/tutorials/step-03-authorization-and-roles.md`, the word list and invariants in `docs/reference/intents-and-invariants.md`, and the affected entries in `docs/reference/glossary.md`. The migration section carries all four before/after pairs of FR-016 — a bare grant, a conditioned grant, the shared guard, a reason-bearing condition — so a reader can convert each without the source. Each case the change introduces appears as a named case, including the timing one, and each appears twice as script and notebook; every example is executed and what it printed is recorded, and a `*.ru_draft.md` sits beside every page written — outside the commit. Local links and anchors are checked, no page still says "four steps" or "five words", and the procedure closes by running the SC-001 search over source, tests, examples and documentation — exempting `check_roles_decorator.py`'s refusal message, the tutorial's migration section and `docs/CHANGELOG.md` — recording the result in `specs/020-roles-without-conditions/evidence/no-removed-names.md`; a hit outside the exempted places sends the page back to be rewritten rather than being explained away.
- [ ] T031 Write the changelog last: one article in `docs/CHANGELOG.md` about what the work created, in plain words — what an author can now write, what the three words mean, the timing change, and the sentinel that now keeps its meaning inside a choice. No per-file account, no commit list, no technical detail; refine an existing entry rather than duplicating it. This is the one page besides the tutorial's migration section that may name a removed word, once, as the thing that went away.

## Dependencies

```text
T001 → T002 → T003
T003 → T004                                          (the new storage shape comes first: everything reads it)
T004 → T005, T006, T007, T009                        (parallel: distinct files)
T005, T006, T007 → T008                              (shares intents/check_roles/__init__.py with T007 and needs the resolver calls gone)
T005, T006, T007, T008, T009 → T010                  (the prose sweep describes what the surgery left)
T010 → T011, T012, T013 → T014                       (US1)
T010 → T015, T016 → T017                             (US2)
T010 → T018, T019, T020 → T021                       (US3)
T010 → T022, T023 → T024                             (US4)
T010 → T025, T026, T027 → T028                       (US5)
T014, T017, T021, T024, T028 → T029 → T030 → T031    (closing, strictly in order)
```

US1–US5 are independent of one another after T010 and may be done in any order; the closing trio is not.

## Parallel execution examples

- After T004: T005, T006, T007 and T009 touch distinct files and can be written together; T008 follows T007 and T005/T006 because it removes what they stop calling and edits the package `__init__.py` they both touch.
- After T010: T011, T012 and T015, T016 and T018, T019, T020 and T022, T023 and T025, T026 touch distinct files and can be written together.
- The example scripts (T027) and the demo actions (T025, T026) are independent of each other but share the same execution environment, so run their verification one at a time.
- The closing trio never runs in parallel: T029 changes the code that T030 documents, and T031 describes what T030 settled.

## MVP scope

The smallest slice that delivers the feature's decision is **Procedure 2 + US1 + US3**: the mechanism is gone, the declaration means roles only, and the vocabulary is three words. That is a coherent, shippable increment for a library user. US2 has almost no implementation of its own (it is the migrated shape plus tests), US4 is the graph view of the same facts, and US5 is the repository catching up; all three are required before the closing trio because the check run covers the demo.

## Format validation

Every task above is `- [ ] Tnnn [P?] [USn?] <action> <path>`: sequential ids, `[P]` only where files are distinct and no incomplete dependency exists in the batch, a story label on every story task and none on setup, foundational or closing tasks, and at least one repository-relative path per task.
