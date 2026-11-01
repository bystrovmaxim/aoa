# Implementation Plan: Check run and CI — decide what runs where

**Branch**: `feature/issue-326-check-run-and-ci` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/045-check-run-and-ci/spec.md`

## Summary

Give every step of the repository's check run one stated home, make CI a real gate on every pull request, and take the network out of the local run. The mechanism is a single step table in `scripts/check_run.py` with three axes per row — `home` (`local`/`ci`/`both`), `fast`, and `browser` — plus selectors (`--where`, `--fast`, `--only-browser`, `--skip-browser`, `--only-group`, `--skip-group`). Local and CI invoke the same table, so they cannot drift.

The package build moves from `python -m build` (which downloads `hatchling` from pypi.org) to `uv build --offline --out-dir packages/<pkg>/dist`; the build and the install smoke move to a CI `packaging` job. The three-engine layout becomes its own CI `browser` job with `~/.cache/ms-playwright` cached by the lockfile hash. The five speed-sensitive test files are marked `benchmark`, CI runs `-m "not benchmark"`, and the tightest wall-clock budgets are widened while the correctness assertions stay exact. The graph step splits into an always-run `check` and a green-only `write`. The local run gains an opt-in `--fast` mode for small changes.

## Technical Context

**Language/Version**: Python 3.12 (packages and `scripts/check_run.py`), TypeScript/Node 22 (Maxitor client), Bash (entry script and CI steps).

**Primary Dependencies**: `uv` (environment and builds), `hatchling` (build backend, served from uv's cache), Playwright 1.64 (three engines), pytest + pytest-asyncio (Python suites), vitest (client unit tests), ruff, mypy, pylint, vulture, radon (static checks).

**Storage**: N/A — no persisted data; the run writes only `archive/logs/check-all.txt` and, on a green local run, the graph files.

**Testing**: pytest for Python (`packages/*/tests`, `tests/`), vitest for the client, Node check scripts for ERD and layout, `tests/scripts/test_check_run.py` for the runner's last-step behaviour (extended for the selectors).

**Target Platform**: the maintainer's macOS machine for the local run; `ubuntu-latest` for CI.

**Project Type**: multi-package Python workspace with a TypeScript front client.

**Performance Goals**: the local full run reaches zero with the network off; the fast mode completes without the client build, the browsers or the packaging; the CI `checks` job stays in the fast-feedback range while `browser` and `packaging` run in parallel.

**Constraints**: no network in the local run; CI on every pull request; the graph files always written or checked; the publish workflow unchanged.

**Scale/Scope**: 44 step rows (35 local, 9 CI-only), 8 packages, 3 CI jobs, 1 local flag set.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. The maintainer decides — commits, PRs and merges only on instruction | The plan prepares a change; no commit, push or merge is part of it. | PASS |
| II. English in commits, in git and in code | Spec, plan, research, contracts and the changelog are English. | PASS |
| III. Module headers | `scripts/check_run.py` already carries the header; no new module under `packages/*/src`. | PASS |
| IV. AI-CORE blocks | `Step` keeps its block; new module-level functions get one where they carry a contract. | PASS |
| V. Short docstrings | New functions get a one-line docstring. | PASS |
| VI. The last three steps: check run, documentation, changelog | The tail is reserved as its own phase with three tasks, in order. | PASS |
| Final step: the check run | The section's description of the local run changes (build and smoke leave it); the agent drafts the amendment and the maintainer ratifies it. | PASS (amended in the tail) |

Post-design re-check: no new gate is violated; the decision table, the contracts and the quickstart agree with the spec.

## Project Structure

### Documentation (this feature)

```text
specs/045-check-run-and-ci/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── check-run-cli.md # Phase 1 output
│   └── ci-jobs.md       # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
scripts/
├── check_run.py             # the step table and the selectors (home, fast, browser)
└── run_checks_with_log.sh   # forwards "$@"; unchanged otherwise

.github/workflows/
├── ci.yml                   # three jobs: checks, browser, packaging
└── publish.yml              # unchanged

packages/maxitor/front/client/
└── scripts/check-layout-determinism.ts   # already exists; no change

packages/aoa-action-machine/tests/action_machine/
├── model/test_navigation_performance.py        # benchmark marker already present
├── bench/test_scoped_logger_hot_path_bench.py  # benchmark marker already present
└── resources/test_pool_bounds.py               # add marker; widen one bound

packages/maxitor/core/graph_compare/tests/
└── test_graph_compare_speed.py                 # add marker

packages/aoa-fastapi-adapter/tests/
└── test_websocket_route.py                     # add marker

tests/scripts/
└── test_check_run.py        # extend for home/fast/browser selectors

docs/
├── ...                      # the one-home table and the fast mode, written in the tail
└── CHANGELOG.md             # one article, written last
```

**Structure Decision**: the change touches the existing runner, the existing CI workflow and the existing test files; no new package or module tree is created. The single source of truth for "where a step runs" is the `STEPS` table in `scripts/check_run.py`, and the spec's decision table is its documentation.

## Implementation Phases

One phase = one commit. The full task breakdown is generated by `/speckit-tasks`.

1. **The decision** — the spec's decision table and the six answered questions (already written to issue #326 and `spec.md`), and the step-table axes (`home`, `fast`, `browser`) with their selectors.
2. **The package steps** — `uv build --offline --out-dir` replaces `python -m build`; build and install smoke move to the CI `packaging` job and leave the local run.
3. **CI** — the three jobs in `ci.yml`; the browser cache; the graph `check`/`write` split.
4. **The speed tests** — the `benchmark` marker on all five files; CI `-m "not benchmark"`; widened budgets.
5. **The fast mode** — `--fast` in the runner and its contract.
6. **The tail** — closing check run, documentation (the one-home table and the fast mode), changelog; the constitution amendment drafted by the agent and ratified by the maintainer.

## Complexity Tracking

No constitution violations; nothing to justify. The selectors are a small addition to an existing dataclass-driven runner, and the three-axis model is the minimum needed to express the decision table without duplicating commands.
