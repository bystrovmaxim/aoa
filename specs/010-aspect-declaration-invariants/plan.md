# Implementation Plan: An aspect declaration's signature is an invariant, not a convention

**Branch**: `feature/issue-193-aspect-decorator-signature-invariants` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-aspect-declaration-invariants/spec.md`

## Summary

Four declaration decorators — `@summary_aspect`, `@regular_aspect`, `@on_error`, `@compensate` — mark methods the engine calls itself, and all four check the **arity alone**. A declaration that renames every parameter, reorders them and leaves them untyped is accepted today; a summary returning `{"not": "a result"}` is handed back as the operation's answer.

The change gives the four the contract `@access_decide` already has, at the same two moments:

1. **At declaration** (in the four decorators): count, names in order, an annotation on every parameter and on the return, and a signature the engine can call positionally. This replaces the count-only invariant that lives in each decorator today.
2. **At assembly** (in the four interchange graph nodes, where the operation's own `Params` and `Result` exist): the types those annotations resolve to — `Params`, `BaseState`, `ToolsBox`, `dict[str, BaseResource]`, `ContextView`, `Exception`, and for a summary the operation's `Result`.

Two refusals are added beside those: a second summary is reported as a second summary (instead of an edge naming a missing node), and a summary whose answer is not its operation's `Result` is refused at assembly (annotation) and at run time (instance) — the path the issue measured as unchecked.

One new shared module, `intents/aspects/aspect_signature.py`, holds the four contracts and the three validators; the reference implementation is `intents/access_decide/access_decide_signature.py`, whose two-moment split, `get_type_hints` use and message shape are followed deliberately. The vocabulary grows by two public errors (`AspectSignatureError`, `DuplicateSummaryAspectError`) and revives a third that is already public and raised nowhere (`ActionResultTypeError`).

The repository's own corpus is part of the change: **499 declarations** do not meet the contract today — 243 in `.py` under `packages/` and `examples/`, 158 in the example notebooks, 98 in `docs/*.md` — and 480 of them are migrated here, because the framework cannot ship examples its own rules refuse. The remaining 19 are wrong on purpose: they are the `pytest.raises` fixtures that prove the refusals fire, and they stay wrong.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`), eight packages under `packages/`.

**Primary Dependencies**: none new. `inspect` for the shape, `typing.get_type_hints` for the types, both already used by `access_decide_signature.py`.

**Storage**: N/A — this is a declaration-time contract, not persisted state. The graph JSON schema is unchanged.

**Testing**: `pytest` per package (`uv run --extra dev pytest packages/aoa-action-machine/tests/ -v`), plus the repository's closing run `bash scripts/run_checks_with_log.sh` (ruff, mypy, pylint, boundaries, metadata, build, vulture, radon, all suites). Verification is adversarial, per `AGENTS.md`: the new test is written first, the code is broken the way it must catch, the test is confirmed to fail alone, the code is restored.

**Target Platform**: the eight Python packages; no browser, no server, no CLI surface changes.

**Project Type**: library monorepo — `packages/aoa-action-machine` is the package that changes; the other seven are consumers and are affected only through their aspect declarations.

**Performance Goals**: the run-time answer check adds one `isinstance` per operation exit. The exit path already calls `ActionSchemaIntentResolver.resolve_result_type(action_cls)` on every run (`aspect_executor.py:215`), so the annotation is resolved once per call today; the plan resolves it once and compares. Target: 10 000 runs of one compliant operation take **at most 5 % longer** than on the tree as it stands, measured on the same machine in the same session (the figures are recorded in the pull request, and a regression beyond the 5 % is treated as a defect rather than as noise). No assembly-time cost is added beyond what `@access_decide` already pays per operation.

**Constraints**: no new dependency, runtime or dev; the closing check run must end green; every new module follows principle III (path on line 1, `═`-ruled sections), every public type carries an AI-CORE block (principle IV), every class, function and method gets a one-line docstring (principle V); all code and history in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 4 decorators, 4 graph nodes, 1 intent resolver, 1 runtime method, 2 new exception modules, 1 new contract module; 763 declarations examined — 343 under `packages/`, 163 under `examples/`, 158 in notebooks, 99 in `docs/*.md` — of which 480 are migrated and 19 remain deliberately wrong.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | The plan describes five phases; each becomes a commit only on instruction. Nothing in the plan commits on its own initiative. |
| II. English in commits and code | Every message, comment, docstring, refusal text in English | All new text is English; the refusal messages quote the parameter names, which are already English identifiers. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled `PURPOSE` / `ARCHITECTURE / DATA FLOW` sections | Applies to the two new exception modules and `aspect_signature.py`; the four decorators and four nodes are edited in place and keep their headers. |
| IV. AI-CORE blocks | Public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `AspectContract` (public class) gets a block, and so do the two new exception classes: they are **new** public types, so the debt the existing exception modules carry is not inherited by adding to it. The block states the rule the error names, which is the whole point of a named error. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol gets one; the touched nodes and decorators keep theirs. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | `tasks.md` will reserve exactly three tail tasks in that order and no other task absorbs them. The corpus migration is **not** a tail task: it is code, and it precedes the check run. |

**Violations requiring justification**: none. The one judgement call — where the shared validator lives — is recorded in [research.md](./research.md) R1 with its rejected alternative.

**Re-checked after Phase 1 design**: unchanged. The design added one module and two exception modules, introduced no dependency, and left every other package's surface as it was; the three tail steps are still reserved for `tasks.md`.

## Project Structure

### Documentation (this feature)

```text
specs/010-aspect-declaration-invariants/
├── plan.md              # This file
├── research.md          # Phase 0 output — the decisions and the measurements
├── data-model.md        # Phase 1 output — the four contracts as data
├── quickstart.md        # Phase 1 output — how to verify this feature by hand
├── contracts/
│   ├── declaration-contract.md   # What each decorator must declare
│   └── refusals.md               # What each refusal says and when it fires
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── intents/aspects/
│   ├── aspect_signature.py                # NEW — the four contracts and the validators
│   ├── summary_aspect_decorator.py         # declaration checks
│   ├── regular_aspect_decorator.py         # declaration checks
│   └── summary_aspect_intent_resolver.py   # the duplicate summary is refused here
├── intents/on_error/on_error_decorator.py
├── intents/compensate/compensate_decorator.py
├── exceptions/
│   ├── aspect_signature_error.py           # NEW
│   └── duplicate_summary_aspect_error.py   # NEW
├── exceptions/__init__.py                  # export the two new names
├── graph/nodes/
│   ├── summary_aspect_graph_node.py        # assembly checks + the answer's annotation
│   ├── regular_aspect_graph_node.py        # assembly checks
│   ├── error_handler_graph_node.py         # assembly checks
│   └── compensator_graph_node.py           # assembly checks
└── runtime/aspect_executor.py              # the summary's answer, at run time

packages/aoa-action-machine/tests/action_machine/
├── intents/aspects/test_aspect_signature_invariants.py   # NEW
├── intents/aspects/test_aspect_decorator_naming.py       # extended
├── intents/aspects/test_aspect_intent_resolver.py        # duplicate summary
├── graph/...                                             # assembly-time refusals
└── runtime/...                                           # the summary's answer

examples/**/*.py, examples/**/*.ipynb, docs/**/*.md       # the corpus migration
```

**Structure Decision**: the change lives in the one package that owns declarations (`aoa-action-machine`) and nowhere else. No new package, no new layer: the shared validator sits beside the decorators that use it, exactly where `access_decide_signature.py` sits beside `@access_decide`.

## Phases

Five phases. Each leaves the tree green, because a phase whose checks refuse declarations the tree still contains is a broken commit rather than a phase — and the repository's rule is one phase, one commit.

1. **The contract, its refusals, and the `.py` corpus.** `aspect_signature.py`, the two exception modules, the declaration checks in the four decorators, the assembly checks in the four nodes, the duplicate summary, the run-time answer check, their tests — and the 224 `.py` sites that the checks would otherwise refuse (61 under `packages/`, 163 under `examples/`). The suite does not run without the `packages/` half, so the engine and that half are one delivery even if they are reviewed as two: the maintainer may split the commit, but not the pair.
2. **The notebooks.** 158 sites in 76 example notebooks, kept step-for-step with their `.py` twins (constitution VI.5). They are not executed by the test suite, so this phase is green on either side of it.
3. **The check run.** `bash scripts/run_checks_with_log.sh` to zero, with the two accepted remarks left alone.
4. **The documentation.** `docs/reference/intents-and-invariants.md` and the 26 pages that show a declaration, written after the code is settled, every case shown and every snippet runnable.
5. **The changelog.** One article in `docs/CHANGELOG.md` about what this work created, in plain words.

Phases 3, 4 and 5 **are** the three reserved tail steps of principle VI — check run, documentation, changelog, in that order. `tasks.md` reserves them as three tasks, and no task in phases 1–2 may absorb them.

## Complexity Tracking

| Decision | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| A shared `aspect_signature.py` instead of per-decorator checks | Four decorators need one message shape, one order rule and one type table; four copies drift, and the refusal text is the feature's user interface | Reusing `access_decide_signature.py` was rejected: its contracts are the object check's four parameters, its return must be a `Verdict`, and it has no `state`, `error` or `state_after` column. Parameterising it into a general "declaration signature" module would rewrite the working, committed object check for no gain. |
| Validation inside the four graph nodes, not in `ActionGraphNode` | The type check needs the operation class, which each interchange node already receives (`_action_cls`); the object check's precedent is identical (`AccessDecideGraphNode.__init__`) | A single check in `ActionGraphNode` was rejected: it would have to find the four callables again and duplicate the resolvers, while the nodes are built from those very callables. |
| 480 corpus sites migrated in this change | The spec's decision: the framework's examples are documentation, and documentation its own rules refuse is worse than none | A deprecation window was rejected in the spec; a partial migration was rejected because the check run cannot be green with the rest left behind. |
