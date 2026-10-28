# Implementation Plan: A Check Run That Measures Itself and Runs Independent Steps Together

**Branch**: `feature/issue-279-parallel-checks` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/032-parallel-checks/spec.md` — issue #279.

## Summary

Time every step of the check run, then run the steps that do not depend on each other at the same time, without changing what is checked or how the log reads. `bash scripts/run_checks_with_log.sh` stays the entry point; it hands over to a new standard-library Python runner, `scripts/check_run.py`, because the system `bash` is 3.2 and has neither a way to wait for whichever job ends first nor a sub-second clock. The runner holds one table of the 37 steps in today's order, runs them in five groups under one limit (`AOA_CHECK_JOBS`, default the number of cores), keeps each step's output apart and joins the log in the table's order at the end. The parallel run ships only if it is green and faster than a measured baseline. Approach and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: Bash (the system's 3.2) for the entry point; Python ≥ 3.12, standard library only, for the runner

**Primary Dependencies**: none new; the runner starts through `uv`, as every Python step already does

**Storage**: N/A — the log file `archive/logs/check-all.txt` (outside git) and per-step files in a temporary folder

**Testing**: the check run itself, before and after; the breaks and repetitions of [quickstart.md](quickstart.md); no new check step (FR-001)

**Target Platform**: the maintainer's macOS (Apple M3 Max, 14 cores, 36 GB) — the baseline machine; Linux is not excluded

**Project Type**: developer tooling inside the monorepo

**Performance Goals**: a wall time lower than the baseline on the same tree and machine (last sequential run: 3 min 41 s)

**Constraints**: same 37 steps and commands; the log reads the same apart from times; `ruff --fix` before any other Python step; Maxitor's package build never during the client build; a limit of 1 gives a sequential run

**Scale/Scope**: one new script (`scripts/check_run.py`), the entry script reduced to its two guards and a hand-over, one new how-to page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it | Pre | Post |
|---|---|---|---|
| I. The maintainer decides | No commit, push or pull request without an instruction in the conversation. | ✅ | ✅ |
| II. English | Code, comments, commits, the issue comments with the baseline: English. Only `tasks.ru_draft.md` and the how-to page's draft are Russian, and neither is committed. | ✅ | ✅ |
| III. Module headers | `scripts/check_run.py` opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW`. | ✅ | ✅ |
| IV. AI-CORE blocks | The runner's public types (the step, the run) carry AI-CORE blocks. | ✅ | ✅ |
| V. Short docstrings | Every class, function and method of the runner has a one-line docstring. | ✅ | ✅ |
| VI. The tail | Three last tasks in order: the check run (which here also proves the change), the documentation, the changelog. | ✅ | ✅ |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` keeps its name, its place and everything it covers; the run may still edit code through `ruff --fix`, before anything else. | ✅ | ✅ |

**VI.5 — script and notebook for each case: decided by the maintainer on 2026-10-28.** The cases of this change are shell commands run on the whole repository (a normal run, a failure, a limit of 1, an invalid limit, an interrupt). The maintainer decided that a how-to page showing each case as its command and what it printed is enough: no `examples/` script and no notebook for this change.

## Project Structure

### Documentation (this feature)

```text
specs/032-parallel-checks/
├── spec.md
├── plan.md                  # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── check-run.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (+ tasks.ru_draft.md, not committed)
```

### Source Code (repository root)

```text
scripts/
├── run_checks_with_log.sh   # entry point: repository checks, the two guards (--guard <name>), hand-over to the runner
└── check_run.py             # NEW: the step table, groups, limit, timing, per-step output, the joined log, interrupt

packages/*/tests/            # only if phase 4 finds a test that fails beside other suites

docs/how-to/run-the-checks.md   # NEW: how the run is ordered, the limit, reading the log (+ .ru_draft.md)
docs/CHANGELOG.md               # one article
```

**Structure Decision**: The runner sits beside the other repository scripts in `scripts/`, which Ruff already lints; nothing goes into a package, because the check run is not part of any published distribution.

## Complexity Tracking

None. VI.5 is settled by the maintainer's decision above (the page, no notebook).
