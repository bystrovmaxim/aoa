# Implementation Plan: Every method of an action gets its own box

**Branch**: `feature/issue-331-every-method-of-an-action-gets-its-own-box` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/048-method-own-box/spec.md`

## Summary

The machine prepares a named `box` in two places today, each by hand. This work moves that preparation into one internal function and calls it for all five kinds of method. `@on_error` gets it with the handler's `state`; `@access_decide` gets it with an empty `state`, at the one spot both its paths go through. No action, signature or public interface changes.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new; the change stays inside `aoa-action-machine`

**Storage**: N/A

**Testing**: pytest, in `packages/aoa-action-machine/tests/action_machine/runtime/`

**Target Platform**: the library, wherever it runs

**Project Type**: Python library in a monorepo of eight packages

**Performance Goals**: none new. A handler's `box` is prepared only when a handler was chosen, and a check's `box` only when the action declares a check, so a run that uses neither pays nothing.

**Constraints**: `ToolsBox` is what action authors hold, so it gains no public method: an action must not be able to name itself (research R1). The access cascade stays free of the log coordinator (R2).

**Scale/Scope**: about 4 source files in one package, 1 new internal module, 1 new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this work meets it | Status |
|---|---|---|
| I. The maintainer decides | Nothing is committed, pushed or opened without an instruction. | Pass |
| II. English | Code, docstrings and commits in English. | Pass |
| III. Module headers | The new module and the new test file start with their path and a module docstring. | Pass |
| IV. AI-CORE blocks | Added only if the new function's shape requires one; it is a function, not a class. | Pass |
| V. Short docstrings | The new function and test helpers carry them. | Pass |
| VI. The last three steps | Three reserved tasks: check run, documentation, changelog. Every case appears as a script and as a notebook, and the examples are executed while written. | Pass |
| Final check run | `check_before_commit.sh` before every commit; `check_before_pr.sh` before the pull request. | Pass |

No violations. Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/048-method-own-box/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/method-box.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/runtime/
├── method_box.py                # new: the one place a method's box is prepared
├── aspect_executor.py           # uses it (regular, summary)
├── saga_coordinator.py          # uses it (compensate)
├── error_handler_executor.py    # uses it (on_error)
├── action_product_machine.py    # uses it (access_decide), in _decide
└── tools_box.py                 # docstring only: no longer "one instance per nesting level"

packages/aoa-action-machine/tests/action_machine/runtime/
└── test_every_method_has_its_own_box.py   # new

docs/reference/intents-and-invariants.md   # the rule and the table
docs/reference/glossary.md                 # "box" says "every aspect" today
docs/tutorials/step-05-error-handling.md   # the handler's log sees state
examples/how_to/09_method_box.py + .ipynb  # every case, as a script and a notebook
docs/CHANGELOG.md                          # one article
```

**Structure Decision**: the change stays in `runtime/`, where the existing two preparations already live. `intents/access_control/cascade.py` and `testing/bench.py` are not touched.

## Phases

One phase is one commit, in the order of issue #331:

1. **`@on_error`**: `method_box.py` appears; regular, summary and compensate move onto it with no change in behaviour; the handler gets its own `box` and `state`. Tests: the handler's log sees `state`, and nested runs and dependencies still work.
2. **`@access_decide`**: `_decide` prepares the check's `box`. Tests: empty `state`, the same answers, `{%state.x}` gives `Undecided`.
3. **The rule's test**: all five kinds, each line's names give a node of the graph, both paths of `@access_decide`. Adversarial breaks as listed in [quickstart.md](quickstart.md).
4. **Closing check run** taken to zero.
5. **Documentation.**
6. **Changelog.** The plan stops here: no release, version bump or publishing.

The method name is asserted only by the rule's test. The tests of phases 1 and 2 assert `state` and behaviour. That split is what lets each break fail exactly one test, as `AGENTS.md` requires.
