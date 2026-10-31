# Implementation Plan: Maxitor Compares Two Versions on Lifecycle Diagrams

**Branch**: `feature/issue-293-lifecycle-diff` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/042-lifecycle-diff/spec.md`

## Summary

The server's lifecycle read gives each state and transition its protocol `id`; nothing else changes on the server, because states and transitions already have a status. The client reads the lifecycle from each version that has it, merges the two, marks each element from the comparison and draws with the existing Graphviz path. The card, the stepper, the filter panel and the hover are those of the use-case diagram, reused. The left panel adds `~` to a lifecycle row from the same comparison.

## Technical Context

**Language/Version**: Python 3.12 (Maxitor's server), TypeScript 5.7, React 19 (client)

**Primary Dependencies**: no new ones; `@hpcc-js/wasm-graphviz`, the existing `ErdFilterPanel`, `DiffCard`, `ChangeStepper`

**Storage**: none

**Testing**: pytest, vitest, the check run, a walk in the browser on `erd-full`

**Target Platform**: as Maxitor: desktop browsers and phone width

**Project Type**: web application (`packages/maxitor/front`, `client/`)

**Performance Goals**: a lifecycle opens in Diff as fast as a use-case diagram; the left panel needs no read beyond the pair's comparison, which it shares

**Constraints**: endpoints only through actions, no new endpoint needed; no test code in production; One's drawing and the marks of the other diagrams untouched

**Scale/Scope**: the demo: 201 lifecycles, 744 states, 1202 transitions, a diagram in tens of elements at most

## Constitution Check

| Rule | State |
|---|---|
| I. Maintainer decides | Pass: each phase's commit waits for the maintainer's word |
| II. English | Pass: only `tasks.ru_draft.md` and the documentation's Russian draft are not |
| III–V. Headers, AI-CORE, docstrings | Pass: applies to every new module and to what is touched |
| VI. Tail | Pass: three reserved tasks, in order; every case as a script and a notebook |
| API only through actions | Pass: an existing action's answer grows by two fields; no new endpoint |

Re-checked after design: no change.

## Project Structure

### Documentation

```text
specs/042-lifecycle-diff/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── maxitor-api.md
│   └── ui.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
packages/maxitor/front/
├── src/maxitor/front/model/diagrams/actions/
│   ├── get_lifecycle_finite_automaton_action.py         # state id, transition id
│   └── get_lifecycle_finite_automaton_action_schema.py  # the same
├── tests/test_get_lifecycle_finite_automaton_action.py
└── client/src/
    ├── api/lifecycleFiniteAutomaton.ts                  # reads a named version too
    ├── model/lifecycleFiniteAutomaton.ts                # id, diff
    ├── lib/lifecycleDiff.ts                             # new: merge, mark, counts, filters, card, changes, load
    ├── lib/lifecycleDiff.test.ts                        # new
    ├── lib/buildLifecycleFsmDotSource.ts                # marks; One's text unchanged
    ├── lib/buildLifecycleFsmDotSource.test.ts           # new or extended: One byte for byte
    ├── lib/sidebarDiff.ts                               # `~` on a lifecycle row
    ├── components/navigation/LeftSidebar/               # draws `~`; expands a row of one version
    └── components/diagrams/LifecycleFsmViewer/          # Diff, card, stepper, panel, hover
.demo-history/build_erd_full.py                          # out of git: the stand's cases
docs/                                                    # the page and its Russian draft, in the closing phase
```

## Phases

One phase, one commit (house rule). The issue's phase 2 is widened: what the spec carries over needs its own commit.

1. **Statuses on lifecycle diagrams, the counts on the button, the left panel** (FR-001 – FR-012, FR-015, FR-026 – FR-031).
2. **The card and the stepper** (FR-013, FR-014, FR-016 – FR-019).
3. **The filter panel, the gear shift, 1-hop and hover** (FR-020 – FR-025).
4. **Closing check run**, then **documentation**, then **changelog**: three commits (FR-032).

The stand's cases are built before phase 1 and extended as phases need them; they are out of git.

## Complexity Tracking

None.
