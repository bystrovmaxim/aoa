# Implementation Plan: Check run — Radon as a real gate, one Ruff step, package builds confirmed

**Branch**: `feature/issue-296-check-run-radon-gate-ruff-builds` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/046-check-run-gates/spec.md`

## Summary

Turn the two Radon steps from printers into gates, with one small script that reads Radon's JSON, fails on complexity grade D or worse and on maintainability grade B or worse, and judges a table of named exceptions. Before the gate goes on, simplify the six D-graded functions and split `test_graph_map.py`, the one module at grade B.

Merge the two Ruff rows into one that fixes locally and only reports in CI. The row uses the table's existing `ci_command`, plus one new field, because `--fast` also takes `ci_command` and would otherwise stop `check_before_commit.sh` from fixing files.

The package builds need no change: #326 already moved them to `uv build`. They are proved identical to the old way, file by file, in a comment on the issue.

## Technical Context

**Language/Version**: Python 3.11+ (`scripts/`, packages), Bash (entry scripts)

**Primary Dependencies**: Radon and Ruff, both already in the `dev` extra; `uv`. No new dependency

**Storage**: N/A

**Testing**: pytest (`tests/scripts/`), plus each package's own suite for the simplified functions

**Target Platform**: Developer macOS, GitHub Actions Linux

**Project Type**: Repository tooling

**Performance Goals**: Whole-run wall time no higher than before (SC-006). The gate adds JSON reading to steps of 4 to 8 s, and the run's longest chain is elsewhere

**Constraints**: No test's meaning changes; CI never changes the tree; `--fast` keeps fixing; Principle I (nothing committed without an instruction)

**Scale/Scope**: 1 new script and its tests, 1 table row merged, 6 functions, 1 test module split, 1 how-to page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Commits are named by phase and made only on instruction | PASS |
| II. English | Code, comments and the issue's comments in English | PASS |
| III. Module headers | The rule covers `packages/*/src`. The script follows the header of its neighbours in `scripts/`; no new `src` module is expected | PASS |
| IV. AI-CORE blocks | Extracted private helpers get a one-line docstring, not a block | PASS |
| V. Short docstrings | Every new function and test has one | PASS |
| VI. The last three steps | Reserved as the last phase with three tasks in order. Cases are shown in `docs/how-to/run-the-checks.md`, from real runs | PASS, see below |
| Final step: the check run | The list names "Ruff lint". It is the maintainer's text: the pull request says so (FR-013), and the agent does not edit it | PASS |

Rules 5 and 6 of Principle VI ask for each case as a script and a notebook. These cases are shell commands against the repository's own check run, so there is no separate script a reader could run. #326, the last change to the check run, was documented the same way. See Complexity Tracking.

**Post-design re-check**: PASS, nothing changed.

## Project Structure

### Documentation (this feature)

```text
specs/046-check-run-gates/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── radon-gate.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
scripts/
├── check_radon.py                 # new: the gate
└── check_run.py                   # one Ruff row; new field `fast_keeps_command`

tests/scripts/
├── test_check_radon.py            # new: every case in the contract
└── test_check_run.py              # one Ruff row in every selection; --fast fixes, CI does not

pyproject.toml                     # tasks `cc` and `mi` call the gate

packages/maxitor/core/graph_map/
├── src/maxitor/graph_map/areas.py       # split_areas
├── src/maxitor/graph_map/assemble.py    # assemble
└── tests/test_graph_map.py              # split into five modules and a helper

packages/maxitor/front/
├── src/maxitor/front/model/diagrams/resources/duckdb_graph_resource.py  # _fill_database
├── src/maxitor/front/model/diagrams/actions/full_graph_action.py        # _build_payload_from_duckdb
└── tests/test_list_entities_lines_on_screen.py

packages/aoa-demo/tests/model/test_examples_generalization_edges.py

docs/how-to/run-the-checks.md
docs/CHANGELOG.md
```

**Structure Decision**: The gate is a script beside its neighbours (`check_no_secrets.py`, `check_package_metadata.py`) and is reached through the existing tasks, so the step table is untouched for Radon.

## Order of the work

Follows the issue's phases, with one correction.

1. **Package builds**: evidence only, in a comment on the issue. No commit.
2. **Radon gate**: one commit. Inside it, the functions and the module are fixed first and the gate goes on last, so the tree never fails its own check.
3. **One Ruff step**: one commit.
4. **Closing**: three commits, in the order of Principle VI.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle VI, rules 5 and 6: no script and notebook pair for each case | The cases are runs of the repository's check run, shown in the how-to with what they really printed | A notebook that shells out to `run_checks_with_log.sh` would repeat the how-to and rewrite the tree when run. The maintainer may rule otherwise when reviewing |
