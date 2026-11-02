# Tasks: Run every check once

**Input**: `specs/050-run-every-check-once/` (spec, plan, research, quickstart)

**Prerequisite (maintainer)**: the constitution passages listed in `plan.md` are changed before the first phase is merged.

## Phase 1: The runner and the scripts (US1, US3)

- [ ] T001 [US1] Remove `scripts/check_before_commit.sh`
- [ ] T002 [US1] Remove `--fast`, its seals and its row fields from `scripts/check_run.py`
- [ ] T003 [US1] Update `tests/scripts/test_check_run.py`; add a test that `--fast` is refused
- [ ] T004 [US3] Confirm by test that the full run's selection is unchanged

**Check**: `tests/scripts/test_check_run.py` only.

## Phase 2: The proof on the commit (US2)

- [ ] T005 [US2] Remove the job `local-run` and update the header comment in `.github/workflows/ci.yml`
- [ ] T006 [US2] Remove `--await-sign-off` and its wait constants from `scripts/check_run.py`, with its tests
- [ ] T007 [US2] Update the header text of `scripts/check_before_pr.sh`: it may run after the pull request opens

**Check**: `tests/scripts/test_check_run.py` only.

## Phase 3: The project rules (US1)

- [ ] T008 [US1] Rewrite the check-script rule in `AGENTS.md`

## Phase 4: The tail

- [ ] T009 Closing check run: CI on the pull request, taken to zero
- [ ] T010 Documentation: `docs/how-to/run-the-checks.md` shows what runs where, with real output
- [ ] T011 Changelog: one article in `docs/CHANGELOG.md`

## Maintainer, at merge

- [ ] T012 In the ruleset of `main`, replace the required check `Proof of the local run` with `Local check run`
