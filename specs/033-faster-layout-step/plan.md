# Implementation Plan: A Faster Three-Engine Layout Step That Checks Exactly as Much

**Branch**: `feature/issue-298-faster-layout-step` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-faster-layout-step/spec.md` — issue #298.

## Summary

The layout step is the check run's longest chain (about 62 s of the run's 85 s). It does three parts one after another — layout hashes (25.2 s alone, with starting Maxitor), pointer in a room (7.2 s), following (27.5 s, six pairs one by one) — although nothing ties their order. The change runs at the same time what does not depend on each other: the six pairs, the two screen sizes within each engine, and part B beside the others. It keeps every check, tolerance and line of output, makes the report's order explicit instead of depending on which context finishes first, and adds the time of each part. Each change is measured and reverted if it does not help. Approach and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: TypeScript run by Node (as today), Playwright for the three engines

**Primary Dependencies**: none new

**Storage**: N/A

**Testing**: the step itself and the check run, before and after; the breaks and repetitions of [quickstart.md](quickstart.md)

**Target Platform**: the maintainer's macOS (Apple M3 Max, 14 cores) — the baseline machine

**Project Type**: developer tooling (a script of the Maxitor client)

**Performance Goals**: the step faster than 59.9 s alone; the check run below 85 s (estimate: the step 15–25 s, the run about 50 s)

**Constraints**: the same 56 page-modes × 3 engines × 2 sizes, the same pointer and following cases and tolerances; the same output lines in the same order apart from times; Maxitor unchanged

**Scale/Scope**: one script, `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts`; the how-to page of the check run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it | Pre | Post |
|---|---|---|---|
| I. The maintainer decides | No commit, push, pull request or issue comment without an instruction in the conversation. | ✅ | ✅ |
| II. English | Code, comments, commits and issue comments in English; only `tasks.ru_draft.md` and the page's draft are Russian, not committed. | ✅ | ✅ |
| III. Module headers | The script keeps its header comment, updated to say which parts run at the same time. | ✅ | ✅ |
| IV. AI-CORE blocks | No new public type; the script's functions keep their one-line doc comments. | ✅ | ✅ |
| V. Short docstrings | Every new or changed function has a one-line doc comment. | ✅ | ✅ |
| VI. The tail | Three last tasks in order: check run, documentation (the how-to page; no `examples/` notebook, as decided for #279), changelog. | ✅ | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/033-faster-layout-step/
├── spec.md
├── plan.md                  # this file
├── research.md
├── quickstart.md
├── contracts/
│   └── layout-step-output.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # + tasks.ru_draft.md, not committed
```

### Source Code (repository root)

```text
packages/aoa-maxitor/client/scripts/check-layout-determinism.ts   # part times; pairs, sizes and part B side by side; explicit report order
packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/{forceLayout,layoutDeterminism}.test.ts   # their own time limit (FR-010's exception)
docs/how-to/run-the-checks.md                                      # the longest chain and the layout step's parts
docs/CHANGELOG.md                                                  # one article
```

**Structure Decision**: Only the step's script changes; it already lives where the check run calls it.

## Complexity Tracking

None.
