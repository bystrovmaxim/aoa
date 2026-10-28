# Tasks: A Check Run That Measures Itself and Runs Independent Steps Together

**Input**: Design documents from `specs/032-parallel-checks/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R10), data-model.md, contracts/check-run.md, quickstart.md

**Tests**: The runner gets no test suite of its own — that would need a new check step, which #279 forbids (research R7). Verification is the check run itself plus the scenarios of quickstart.md, done adversarially: break the thing the scenario must catch, confirm only that step fails, restore.

**Organization**: one phase = one commit, in the order of #279's phases. Phase 6 of #279 is three commits (check run, documentation, changelog). A phase that ends with nothing to commit says so in its last task.

**Issue checkboxes**: #279 "Phases" has six. Commit 2 → phase 1; commit 3 → phase 2; commit 4 → phase 3; commit 5 → phase 4; the measurement (Phase 6 here) → phase 5; commits 6–8 → phase 6 (ticked after commit 8). Each tick carries its sha (`gh issue edit 279`). Commit 1 (design documents) has no issue phase. Comments on #279 (the baseline, the measurement) are posted only on the maintainer's word.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US4)
- `scripts/check_run.py` opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); its public types carry AI-CORE blocks (IV); every class, function and method a one-line docstring (V).
- `$SCRATCH` below is the session's scratch folder, never the repository.

---

## Phase 1: Setup — design documents (commit 1)

- [ ] T001 Prepare commit 1 with `specs/032-parallel-checks/` only (spec, plan, research, data model, contract, quickstart, `checklists/requirements.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify the parallel check run (#279)`. `.claude/launch.json` stays out.

---

## Phase 2: The runner, sequential, with times (commit 2) · US1 — #279 phase 1

**Goal**: every step timed, the run's wall time printed, nothing else changed (FR-001, FR-002).

**Independent Test**: quickstart §1 and §2.

- [ ] T002 Before any change: run `bash scripts/run_checks_with_log.sh` on the clean branch (still `main`'s script) and keep the log as `$SCRATCH/check-all.before.txt`; note its start and end times. It is the "before" of quickstart §2.
- [ ] T003 [US1] Create `scripts/check_run.py` (standard library only): the step table of the 37 steps in today's order with today's names and commands, copied verbatim from `scripts/run_checks_with_log.sh` (the two guards as `bash scripts/run_checks_with_log.sh --guard lazy-init-getattr` / `--guard client-component-readmes`, shown in the log as today's `check_no_lazy_init_getattr (shell function)` and `check_maxitor_client_component_readmes (shell function)`; the eight builds unrolled from the loop); each row with `name`, `command`, `group`, `after`, `not_during` as in data-model.md, filled now though only the order is used in this phase. Steps run one after another; each command through `bash -c` from the repository root; output appended to the log as today; the `OK`/`FAIL` line gets the duration — `OK <name> (exit 0, 12.3 s)` — measured with a monotonic clock to a tenth of a second, on the console too; the footer gains `Wall time: <s> s`. Exit 1 if any step failed, else 0.
- [ ] T004 [US1] Reduce `scripts/run_checks_with_log.sh` to: finding the repository root and the `pyproject.toml` check as today (exit 2 now, per contracts/check-run.md, instead of 1), the two guard functions unchanged, a `--guard <name>` switch that runs one of them and exits with its result, and the hand-over `exec uv run --extra dev python scripts/check_run.py "$@"`. The comments about the two accepted remarks and about the auto-fix scope move to the runner beside their steps, word for word.
- [ ] T005 [US1] Verify: two runs on a clean tree, both green; quickstart §2 — the log matches `$SCRATCH/check-all.before.txt` apart from durations, dates and output that varies by itself; 37 `OK` lines, each with a duration. Break: make one guard fail (a `__getattr__` in a scratch `__init__.py` under `packages/`) → only that step is `FAIL`, exit 1; restore. Record both runs' per-step and wall times here.
- [ ] T006 [US1] Prepare commit 2: `feat(scripts): time every step of the check run (#279)`; tick #279 phase 1 with its sha. Post the two baseline runs' per-step and wall times as a comment on #279 when the maintainer says so.

---

## Phase 3: One output file per step, joined in order (commit 3) · US2 — #279 phase 2

**Goal**: where output goes is separated from when steps run; the log reads as phase 2's (FR-003, FR-004).

**Independent Test**: quickstart §2 against the log of phase 2.

- [ ] T007 [US2] In `scripts/check_run.py`: each step writes its output into its own file in a temporary folder; when all steps have ended, the log is written in the table's order — today's header, one block per step (`=== <name> ===`, `$ <command>`, blank, output, blank, `OK`/`FAIL` line with duration), today's footer with `Wall time` — exactly the format of contracts/check-run.md. The console keeps printing `> <name>` and the result line as each step starts and ends. The temporary folder is removed at the end.
- [ ] T008 [US2] Verify: a clean run's log matches phase 2's apart from times; a step that prints nothing still has its block in place (check with a guard, which prints nothing when it passes). Record here.
- [ ] T009 [US2] Prepare commit 3: `refactor(scripts): keep each step's output apart, join the log in order (#279)`; tick #279 phase 2.

---

## Phase 4: Groups, the limit and interrupt (commit 4) · US3 — #279 phase 3

**Goal**: independent steps run at the same time under one limit; every failure still reported; Ctrl+C leaves nothing running (FR-005 – FR-010).

**Independent Test**: quickstart §3, §4, §5.

- [ ] T010 [US3] In `scripts/check_run.py`: the scheduler of research R3 — the two guards and `ruff check --fix` first, in order, alone; then every step whose `after` steps have all ended and none of whose `not_during` steps is running, as long as fewer than the limit are running; ties go in table order. The limit comes from `AOA_CHECK_JOBS` (default `os.cpu_count()`); a value that is not a positive whole number prints a message naming the variable and the value and exits 2 before any step. A failed step does not stop others, and steps after it still run (R6).
- [ ] T011 [US3] Interrupt (R6): every step starts in its own process group; on SIGINT or SIGTERM the runner sends SIGTERM to every running group, waits up to 5 s, sends SIGKILL to what is left, writes the log of the steps that ended followed by `Run interrupted`, and exits 130.
- [ ] T012 [US3] Verify, one at a time, restoring each: quickstart §3 (a limit of 1 and the default give the same log apart from times; `AOA_CHECK_JOBS=0` and `=abc` exit 2 before any step); §4 — a failing client unit test, a mypy error, a broken `pyproject.toml` in one package, a failing test in one package — each time only the broken step (and the packaging smoke test after a failed build) is `FAIL`, all others report, exit 1; §5 — Ctrl+C during the tests gives exit 130, `pgrep` finds nothing, the log ends with `Run interrupted`. Also confirm from the console order that `ruff --fix` ended before any other Python step started and that the Maxitor build did not overlap the client build. Record here.
- [ ] T013 [US3] Prepare commit 4: `feat(scripts): run independent checks together under one limit (#279)`; tick #279 phase 3.

---

## Phase 5: Tests that do not share anything (commit 5) · US4 — #279 phase 4

**Goal**: the eight test suites pass side by side as they pass alone (FR-011).

**Independent Test**: quickstart §6.

- [ ] T014 [US4] Ten parallel runs in a row on a clean tree; record each run's result and wall time here. For every test that fails only in a parallel run: find what it shares (a fixed port, a shared file, a shared database, a time limit under load) and fix the test in its package's `tests/`; break-check the fix (restore the shared resource → that test fails again beside the others, and only it). A test that cannot be fixed here: its package's step gets `not_during` every other test step in `scripts/check_run.py`, with the reason in a comment.
- [ ] T015 [US4] Prepare commit 5 with the test fixes: `test: let package suites run side by side (#279)`; tick #279 phase 4. If ten runs were green with no fix, there is nothing to commit: record that here and tick phase 4 with "no change needed".

---

## Phase 6: Measure and decide · #279 phase 5

**Goal**: the parallel run ships only if it is green and faster (FR-012, SC-002).

- [ ] T016 Two parallel runs on the same clean tree and machine as T005; record per-step and wall times beside the baseline here. If both are green and faster: post the comparison on #279 when the maintainer says so, and tick #279 phase 5. If not: write here what stood in the way and stop for the maintainer's decision — FR-012 then keeps only phases 2–3 (timing and the joined log) and drops phase 4's scheduling.

---

## Phase 7: The check run (commit 6) · #279 phase 6

- [ ] T017 Run `bash scripts/run_checks_with_log.sh` and take it to zero — only the two accepted remarks stay; prepare commit 6: `chore: take the check run to zero (#279)`. If the first run is already clean there is nothing to commit; record that here.

---

## Phase 8: Documentation (commit 7) · #279 phase 6

- [ ] T018 Write `docs/how-to/run-the-checks.md` — the maintainer's decision: the page alone, no `examples/` script and no notebook (plan, VI.5). It shows, each as the command and what it really printed: a normal run and how its log is laid out; the groups and what waits for what; the limit, its default and `AOA_CHECK_JOBS=1`; an invalid limit; a failing step and how to find it in the log; an interrupt. Link it from `docs/index.md` where the how-to pages are listed. The Russian draft beside it (`docs/how-to/run-the-checks.ru_draft.md`, not committed). Prepare commit 7: `docs(how-to): run the checks (#279)`.

---

## Phase 9: Changelog (commit 8) · #279 phase 6

- [ ] T019 One article at the top of `docs/CHANGELOG.md` about what this work gives: the check run shows where its time goes and finishes sooner, its log reads as before, and the limit can be set — plain words, no technical detail (constitution VI); its Russian version in `docs/CHANGELOG.ru_draft.md`. Prepare commit 8: `docs(changelog): a check run that shows its time and finishes sooner (#279)`; tick #279 phase 6.

---

## Dependencies & Execution Order

- Phases in order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. Each phase builds on the previous one's runner; Phase 6's decision can remove Phase 4's scheduling from what ships.
- T002 runs before any change to the script.
- No commit, push, pull request or issue comment without the maintainer's word in the conversation (constitution I).

## Parallel Opportunities

- Little inside phases: the runner is one file. In Phase 5, fixes to different packages' tests are independent of each other.

## Implementation Strategy

- The result is the whole of Phases 2–6: a timed, readable, parallel run that is faster — or, if Phase 6 says it is not, the timing and the joined log alone (FR-012).
- Then the tail — check run, documentation, changelog — closes #279. After the merge into `main`, `main` is brought into `feature/issue-273-graph-history` so the graph-history work runs on the new check run. Then #296: drop or speed up steps that cost time and catch nothing.
