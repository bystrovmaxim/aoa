# Implementation Plan: Roles Without Conditions

**Branch**: `feature/issue-248-check-roles-without-grant-guard` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Clarified specification, the maintainer's answers in [spec.md](spec.md#clarifications), and [issue #248](https://github.com/bystrovmaxim/aoa/issues/248).

## Summary

`@check_roles` becomes the whole role layer: it declares a role, a choice between roles, or a
sentinel, and nothing else. `grant`, `Grant`, `guard=`, `guard_reason=`, `Gate.WHEN` and
`Gate.GUARD` disappear, and with them the per-grant and shared conditions, the fourth cascade step
and the graph data that carried them. Conditional authorization — object rules, user-and-request
facts, reasons — lives in `@access_decide`, which already has the shape for it.

Three published words remain: who is calling, which roles are held, what the object rule decides.
A sentinel written beside ordinary roles keeps the meaning it has alone. The repository's own
declarations, tests, demo and example pages migrate with the change.

Research and design below are workflow procedures, not repository commit phases. This command
performs no commits and creates no implementation task list; `/speckit-tasks` produces that.

## Technical Context

**Language/Version**: Python >=3.12 (local interpreter 3.12.12). No new dependency, no new package.

**Primary Dependencies**: existing Pydantic >=2 (local 2.12.5), pytest (local 8.4.2), the existing
`aoa-action-machine` intent/decorator/graph machinery. Maxitor's Python and TypeScript client are
consumers and are not modified.

**Storage**: none. A decision is not persisted by this change; the graph payload loses two
properties and gains nothing. No migration of stored data is required — a search of Maxitor's
sources finds no gate word and no reader of `guard`/`guard_reason`.

**Testing**: pytest per package (`uv run --extra dev pytest packages/<pkg>/tests -v`), the
repository's closing runner `scripts/run_checks_with_log.sh`, and executed example scripts and
notebooks for the documentation step.

**Target Platform**: the existing Python library environments; Maxitor browser client unchanged.

**Project Type**: public library packages (intents, decorators, graph interchange) plus a demo
package and teaching material.

**Performance Goals**: no target is invented. The change deletes work: the role step stops
evaluating callables, the cascade runs one fewer step before the run, and the graph builds one edge
per role instead of one per grant. Role matching stays linear in the caller's role count.

**Constraints**: Python only, no new dependency; the whole repository including `aoa-demo` must be
green because the closing runner covers it; English in code, tests, docs and the changelog; the
work is prepared and shown but never committed, pushed, opened or merged without the maintainer's
word (Principle I); the constitution is read, not amended.

**Scale/Scope**: two source packages touched (`aoa-action-machine`, `aoa-demo`), one checked but
unchanged consumer (`aoa-maxitor`); 17 test modules name the removed mechanism — 15 migrated in
place (13 in the package plus the demo's 2), 1 replaced by a removal test, 1 deleted with the
pairing rule it tested — and one further module outside them is deleted because its subject is a
deleted exception; 6 example scripts and their 6 notebooks rewritten; 3 documentation pages
updated (tutorial, reference, glossary) plus their Russian drafts; 1 changelog article.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS with the reading recorded below.*

| Principle | Design evidence |
| --- | --- |
| I — the maintainer decides | The branch already exists at the maintainer's instruction. This plan and every phase below are prepared work; no commit, push, pull request or merge happens without a separate explicit instruction. |
| II — English in commits and code | Every artifact, docstring, test name, docstring example and changelog line written by this feature is English. |
| III — module headers | Every touched module keeps its relative-path first line; the renamed demo actions carry the same header, `PURPOSE` and `ARCHITECTURE / DATA FLOW` sections. |
| IV — AI-CORE blocks | The blocks that describe the changed surface are rewritten, not deleted: `Gate`, `Refused`, `Undecided`, `RoleGraphEdge`, `ActionGraphNode`, `RoleGraphNode`, `CheckRolesIntentResolver`. No block goes on a method or into a module docstring. |
| V — short docstrings | Every new or touched class, function and method carries the one-line purpose; the removed ones take their docstrings with them. |
| VI — check run, then documentation, then changelog | Reserved as C1, C2, C3 below, in that order, and no work package absorbs them. |
| Adversarial verification | The five mutations of FR-018 run against a temporary copy with valid neighbouring controls; a mutation that does not fail its check means the test is wrong. |
| Governing text | The constitution is read and cited, never edited in this change. |

**One reading is recorded rather than assumed.** Principle VI puts the check run before the
documentation. The example scripts under `examples/step_03_authorization_and_roles/` are executable
Python that uses the removed API, so W6 migrates them (and their notebooks) as code while C2 owns
the prose: the tutorial, the reference, the glossary, the page narrative, the Russian drafts and the
recorded output. The alternative — leaving the examples on a removed API until after the check run —
would make the checked tree contain code that cannot import. The check run does not execute
examples, so C1's green result does not depend on this choice; C2 executes and records them again
against the settled code.

## Project Structure

### Documentation (this feature)

```text
specs/020-roles-without-conditions/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── role-declaration.md
    ├── decision-and-cascade.md
    └── graph-projection.md
```

[tasks.md](tasks.md) is generated by `/speckit-tasks`; it is not produced here.

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── intents/check_roles/{__init__,check_roles_decorator,check_roles_intent,
│   │                          check_roles_intent_resolver}.py
│   ├── intents/access_control/{gate,cascade,roles,undecided,refused,__init__}.py
│   ├── graph/edges/role_graph_edge.py
│   ├── graph/nodes/{action_graph_node,role_graph_node}.py
│   └── exceptions/{__init__,authorization_error}.py
└── tests/action_machine/{intents,graph,runtime,exceptions}/
packages/aoa-demo/
├── src/aoa/demo/fastapi_mcp_services/actions/cancel_order.py
├── src/aoa/demo/model/access_cascade/actions/…            # two shapes renamed
└── tests/{fastapi_mcp_services,model}/
examples/step_03_authorization_and_roles/                  # six pages, scripts + notebooks
docs/{tutorials/step-03-authorization-and-roles.md,reference/intents-and-invariants.md,
      reference/glossary.md,CHANGELOG.md}
```

Deleted with the mechanism: `intents/check_roles/grant.py`,
`intents/check_roles/reason_validation.py`, `exceptions/access_condition_async_error.py`,
`exceptions/condition_reason_error.py`, and the tests whose only subject they were.

**Structure Decision**: remove code, do not build a replacement. The role layer keeps
`CheckRolesIntent` → `@check_roles` → `_role_info["spec"]` → `RoleGraphEdge` / `RoleChecker`; the
object layer keeps `@access_decide` → `access_decide` edges → `AccessDecideGraphNode`. Nothing new
enters the public surface, and no module changes its role.

## Scope and unchanged behavior

- Unchanged: role matching by subclassing, `RoleMode` and all four members, the mandatory
  `@check_roles` refusal, inherited declarations, `GuestRole` and `AnyRole` alone, the
  `@access_decide` contract (signature, suffix, description, `@context_requires`, "at most one",
  "never inherited", the three answers), `FORBIDDEN_OBJECT`, the two-phase seam of the cascade, the
  decision event, and the exported shape of every graph payload.
- Changed deliberately: a sentinel beside ordinary roles stops being an unsatisfiable alternative
  (FR-013, SC-003 names the tests whose outcome therefore moves).
- Changed as a consequence: a former condition refuses inside the run instead of before it
  (FR-017), and the words `WHEN`/`GUARD` are gone rather than deprecated (FR-004).
- Out of scope: role checks inside `@access_decide`, a `has_role` helper, removing `@check_roles`,
  new `RoleMode` semantics, a new authorization declaration, runtime sandboxing, rewriting
  `packages/*/CHANGELOG.md` history.

## Design and implementation work packages

The six packages below are the design view; [tasks.md](tasks.md) realises them as T004–T028.
W1–W4 are one foundational procedure (T004–T010) because the mechanism cannot be deleted piecemeal
while the package still imports; W5 spans the five story procedures (T011–T024); W6 is T025–T028.

### W1 — One declaration, roles only (FR-001, FR-002, FR-006, FR-012)

Rewrite `check_roles_decorator.py` around a single normalization path: one or more role arguments,
or one tuple/list; sentinels accepted anywhere; every member validated as a `BaseRole` subclass;
`UNUSED` refused and `DEPRECATED` warned exactly as today. The decorator's signature gains
`**unsupported` so the three removed keywords are refused with the migration message of
[the declaration contract](contracts/role-declaration.md#refused-forms), and any other keyword is
refused with the accepted forms named. Storage becomes `_role_info = {"spec": ...}`.

Delete `grant.py` with `Grant`/`grant`, and delete what loses its last user with it:
`reason_validation.py`, `AccessConditionAsyncError`, `ConditionReasonError`, their `__all__` entries,
their imports, and `resolve_grants`/`resolve_guard`/`resolve_guard_reason` from the resolver. Keep
`resolve_check_roles` and `resolve_role_mode`. Rewrite the AI-CORE block of
`CheckRolesIntentResolver` and the module docstrings of `CheckRolesIntent` and the package
`__init__` so they describe one declaration instead of two forms.

### W2 — The role step answers one question (FR-003, FR-013)

Rewrite `RoleChecker.check` around the single spec: build the alternatives, collapse duplicates by
identity in declaration order, then answer `None` for a declaration containing `GuestRole`, answer
for `AnyRole` only when the caller holds at least one active role, otherwise match by `issubclass`
over the caller's non-silenced roles and answer `Refused(gate=Gate.CHECK_ROLES)` when nothing
matches. `_spec_from_grants`, `_sentinel_answer`, `_concrete_answer` and the `role_matched` /
`refused_reason` bookkeeping go; the module header describes one step with one answer.

### W3 — Three words and three steps (FR-004, FR-005, FR-017)

`gate.py` keeps three members and states three in its header and table. `cascade.py` loses
`guard_answer`, `guard_gate`, their `__all__` entries and their `_STEPS` entries;
`GATES_BEFORE_RUN` becomes the two remaining pre-run steps; the header says three ordered steps and
three answers; `roles_gate` claims `CHECK_ROLES` only. `undecided.py`, `refused.py` and
`access_control/__init__.py` lose every mention of the removed words, including the `Gate.GUARD`
example in the `Undecided` block. `authorization_error.py` stops explaining level `2`. Nothing
anywhere reintroduces a pre-run hook; the timing consequence is stated where an author reads the
cascade.

### W4 — The graph says roles, and points at the rule (FR-010, FR-011)

`RoleGraphEdge` takes a role class only, keeps `properties={}`, exports the same wire shape, and
`get_role_edges` reads the spec and deduplicates per W2. `ActionGraphNode.properties` loses `guard`
and `guard_reason` with the docstrings that justified them. `RoleGraphNode`'s invariant text drops
the "conditions belong on the edge" paragraph, because there are no conditions. No new property is
added: the `AccessDecide` node is the statement (verified in research R10 — Maxitor names no gate
word and requires no property this change removes).

### W5 — The package's own tests (FR-018, SC-003)

Migrate the fifteen `aoa-action-machine` test modules that name the removed mechanism. Keep each
module's subject: a module about the shared condition becomes a module about the object rule's
branch; a module about a grant's condition becomes a module about the migration message; the
cascade-order, gate-order, verdict, event and machine-decision modules keep their subjects and
change only their declarations. Add the five adversarial mutations of FR-018 as tests beside them,
each with a valid neighbouring control. Assert the new declaration outcomes from FR-013 explicitly
— the open choice, the at-least-one-role choice, and the collapsed duplicate — because those are the
only role outcomes that move.

### W6 — The repository's own declarations (FR-014)

Migrate the three demo actions and their two test modules per research R11, including the two file
renames and `actions/__init__.py`. Migrate the six example scripts and their six notebooks so the
tree contains no code that cannot import: the four pages that taught the removed words are renamed
to what they now teach (`02_object_rule`, `03_shared_object_rule`, `17_branch_order`,
`22_reason_in_branch`) and keep their numbers; `07_three_answers` and `13_cascade` keep their names
and teach three words instead of five. Every script is executed while it is written; the notebooks
follow the same steps.

## Closing tasks reserved for `/speckit-tasks`

Exactly three tail tasks, in this order, and no work package may absorb them.

1. **C1 — The check run, taken to zero.** `bash scripts/run_checks_with_log.sh`, every remark fixed,
   including the demo package, Ruff/mypy/pylint/vulture/Radon and the packaging smoke. The two
   accepted third-party remarks stay. A failing check is repaired, not triaged.
2. **C2 — The documentation.** Written after the code is settled: the tutorial's condition sections
   and its migration section, the reference that states the words and the invariants, the glossary,
   the example pages' own narrative and recorded output, and a Russian draft beside every page
   written (drafts stay outside the commit). Every case the change introduces appears as a case, and
   every example is executed with what it prints recorded.
3. **C3 — The changelog, one article.** `docs/CHANGELOG.md` gains a single readable piece about
   what the work created, the nuances a user has to know (the timing change, the sentinel in a
   choice, the words that are gone), and no per-file account.

## Verification design

[quickstart.md](quickstart.md) holds the runnable scenarios S1–S9; this section says what they
partition.

- **Declaration**: every accepted form, every refused form, the migration message, and the
  duplicate collapse — one test each, with the message asserted, not just the exception type.
- **Matching**: sentinel-first, `AnyRole`, silenced roles, `UNUSED`/`DEPRECATED`, and an operation
  without `@check_roles`.
- **Answers**: the three words, the rejection of a stored `WHEN`/`GUARD`, the two phases of the
  order, `Undecided` on a raise, `Undecided` on a wrong return type.
- **Graph**: one edge per distinct role, empty exported properties, an action node without
  condition data, an `AccessDecide` node present exactly when declared.
- **Migration**: the demo's three actions, six example scripts and six notebooks executing with
  recorded output, and the tutorial/reference/glossary containing no instruction that names a
  removed declaration.
- **Adversarial**: the five mutations of FR-018 in a temporary copy, each failing its targeted check
  while its control passes.

## Research and design gates

- Research complete: [research.md](research.md) records the thirteen decisions, each with the file
  and line that justified it and the alternative rejected.
- Data view: [data-model.md](data-model.md) defines the declaration, the object rule, the answer,
  the word and the order.
- Interfaces: [role declaration](contracts/role-declaration.md),
  [answers and order](contracts/decision-and-cascade.md),
  [graph projection](contracts/graph-projection.md).
- No open question remains: every open question of issue #248 §8 is closed in the specification's
  Clarifications section, and the two questions clarify raised are integrated into FR-008 and
  FR-013.
- No gate failure. The only recorded reading is the examples-versus-check-run order explained above.

## Complexity Tracking

No constitutional exception is introduced. The change is subtractive: four modules and roughly
fifteen test subjects disappear, no dependency is added, no new public name is created, and no
second declaration layer replaces the removed one. The single deliberate behaviour change — a
sentinel inside a choice — is named in the specification, the plan, the tests and the changelog
rather than absorbed quietly.
