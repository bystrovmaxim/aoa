# Implementation Plan: Run every check once

**Branch**: `feature/issue-351-run-every-check-once` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/050-run-every-check-once/spec.md`

## Summary

CI becomes the closing check run. The local machine runs only the tests of each phase and the browser run. `scripts/check_before_commit.sh` and the `--fast` mode it was the only caller of are removed. The merge rule of `main` requires the commit status `Local check run` directly, which replaces CI's waiting job, so the proof may arrive at any moment after the pull request opens.

## Technical Context

**Language/Version**: Python 3.12 (standard library runner), bash, GitHub Actions YAML

**Primary Dependencies**: `gh` CLI for the sign-off, GitHub rulesets

**Storage**: N/A

**Testing**: pytest, `tests/scripts/test_check_run.py`

**Target Platform**: developer machine and GitHub-hosted runners

**Project Type**: repository tooling

**Performance Goals**: no CI minutes spent waiting for the proof

**Constraints**: the ruleset change is made on GitHub, in the same moment the job is removed from the requirement

**Scale/Scope**: two scripts, the runner, one workflow, `AGENTS.md`, one how-to page

## Constitution Check

| Rule | Status |
|------|--------|
| I. The maintainer decides | Pass: nothing is committed, pushed or changed on GitHub without an instruction |
| II. English | Pass |
| III-V. Headers, AI-CORE, docstrings | Pass: touched runner code keeps its form |
| VI. The last three steps | **Depends on the maintainer**: step 1 names a local `run_checks_with_log.sh`; the tail keeps its three tasks |
| Final step: the check run | **Depends on the maintainer**: see below |

### Maintainer's dependency

Before the first phase is merged, the maintainer changes `.specify/memory/constitution.md`:

1. **Principle VI, step 1**: the closing check run is CI's run on the pull request, taken to zero.
2. **Final step, rules 1-2**: `check_before_commit.sh` is gone; a pull request may open before `check_before_pr.sh` has passed; the proof is required by the merge rule directly, not by the job `Proof of the local run`.

## Project Structure

### Documentation (this feature)

```text
specs/050-run-every-check-once/
├── plan.md
├── research.md
├── quickstart.md
└── tasks.md
```

`data-model.md` and `contracts/` are omitted: the feature has no data and no new interface.

### Source Code (repository root)

```text
.github/workflows/ci.yml        # job local-run removed, header comment updated
scripts/check_before_commit.sh  # removed
scripts/check_before_pr.sh      # header text
scripts/check_run.py            # --fast and --await-sign-off removed
tests/scripts/test_check_run.py # follows the runner
AGENTS.md                       # the check-script rule
docs/how-to/run-the-checks.md   # what runs where
docs/CHANGELOG.md               # one article
```

## Complexity Tracking

None: the change removes code.
