# Tasks: A Faster Three-Engine Layout Step That Checks Exactly as Much

**Input**: Design documents from `specs/033-faster-layout-step/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R7), contracts/layout-step-output.md, quickstart.md

**Tests**: The step is itself a check; it gets no test suite of its own (it would need a new check step). Verification is the step and the check run before and after, and the breaks of quickstart §4, done adversarially: break what must be caught, confirm only that line fails, restore.

**Organization**: one phase = one commit, in the order of #298's phases; #298 phase 6 is three commits. A phase whose change does not make the step faster is reverted (FR-008) and ends with nothing to commit; its last task says so.

**Issue checkboxes**: #298 "Phases" has six. Commit 2 → phase 1; commit 3 → phase 2; commit 4 → phase 3; commit 5 → phase 4; the measurement (Phase 6 here) → phase 5; commits 6–8 → phase 6 (ticked after commit 8). Each tick carries its sha. Comments on #298 are posted only on the maintainer's word.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US4)
- The script is `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts`; every new or changed function has a one-line doc comment, and the header comment says what runs at the same time.
- `$SCRATCH` is the session's scratch folder, never the repository.

---

## Phase 1: Setup — design documents (commit 1)

- [ ] T001 Prepare commit 1 with `specs/033-faster-layout-step/` only (spec, plan, research, contract, quickstart, `checklists/requirements.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify the faster layout step (#298)`. `.claude/launch.json` stays out.

---

## Phase 2: Time the parts (commit 2) · US1 — #298 phase 1

**Goal**: the step prints the time of each part and the total; nothing else changes (FR-002, FR-003).

- [X] T002 Before any change: run the step alone twice from `packages/aoa-maxitor/client` (`node scripts/check-layout-determinism.ts`) and keep the second output as `$SCRATCH/layout.before.txt`; record both totals here. Done on `3029b5b3`: two runs alone, both green, 60 s and 59 s; the second kept as `layout.before.txt` (66 lines).
- [X] T003 [US1] In the script's `main`: note the time around part A (`runEngine` for all engines and `report`), part B (`pointerCase` for all engines) and part C (the pairs), and print `part A (layout hashes) <s> s`, `part B (pointer in a room) <s> s`, `part C (following) <s> s` before the summary line (contracts/layout-step-output.md, line 4). Done: `partA` / `partB` / `partC` timestamps around the three parts and a `seconds()` helper; three `part …` lines before the summary. Part A is timed from the first engine's start to the end of its report, so starting the servers and Maxitor (about 1.4 s) is outside the parts and inside the summary's total. The script was not Prettier-formatted before and the client has no Prettier config, so it is not reformatted.
- [X] T004 [US1] Verify: twice alone and once inside the check run, all green; quickstart §2 — the output equals `layout.before.txt` apart from times and the three new lines. Record the part times and the step's time in the check run here — the baseline. Done. Alone: part A 23.6 / 23.5 s, part B 7.2 / 7.1 s, part C 27.4 / 27.3 s, total 59 / 59 s, exit 0; with times and the part lines stripped, the output equals `layout.before.txt`. Inside the check run (green, 37 `OK`, wall 86.3 s): the step 63.1 s — part A 24.8 s, part B 7.2 s, part C 27.4 s. This is the baseline.
- [X] T005 [US1] Prepare commit 2: `feat(maxitor): time the parts of the layout step (#298)`; tick #298 phase 1. Post the baseline on #298 when the maintainer says so. Done: committed as commit 2; #298 phase 1 ticked; the baseline posted on #298.

---

## Phase 3: The six pairs side by side (commit 3) · US2 — #298 phase 2

- [ ] T006 [US2] Part C: start all six `followCase` calls at once (each still opens its own new room), wait for all, then print their lines in today's pair order (research R2).
- [ ] T007 [US2] Verify: twice alone, once in the check run, green; output as before apart from times; part C's time before and after. Break (R5): add 3 px to one pair's `apartPx` → only that pair's line is `DIFF`, exit 1; restore. If part C is not faster or a run fails: revert, record why, and try the fallback of R2 (three groups by leading engine) under the same checks.
- [ ] T008 [US2] Prepare commit 3: `perf(maxitor): run the following pairs of the layout step together (#298)`; tick #298 phase 2 — or, if reverted, record "no change" and tick it so.

---

## Phase 4: The two screen sizes side by side (commit 4) · US2 — #298 phase 3

- [ ] T009 [US2] Part A: in `runEngine`, create both contexts and lay out the targets in both at once (research R3). `report` walks the targets in the left panel's order and each target's modes in page order instead of the map's insertion order; a `DIFF` lists runs in engine-then-size order.
- [ ] T010 [US2] Verify: twice alone, once in the check run, green; output as before apart from times; part A's time before and after. Break (R5): a suffix on Firefox's hash for one page-mode at 1600x900 → only that page-mode is `DIFF`, its runs listed in engine-then-size order, exit 1; restore. Revert if not faster or not green.
- [ ] T011 [US2] Prepare commit 4: `perf(maxitor): lay out both screen sizes at once in the layout step (#298)`; tick #298 phase 3 — or record "no change".

---

## Phase 5: Part B beside the rest (commit 5) · US2 — #298 phase 4

- [ ] T012 [US2] In `main`: start parts A, B and C at once, wait for all three, then print part A's report, part B's lines, part C's lines and the part times, in that order (research R4).
- [ ] T013 [US2] Verify: twice alone, once in the check run, green; output as before apart from times; the step's time before and after. Break (R5): add 3 px to WebKit's pointer offsets → only `pointer in a room | webkit` is `DIFF`, exit 1; restore. Revert if not faster or not green.
- [ ] T014 [US2] Prepare commit 5: `perf(maxitor): run the layout step's parts together (#298)`; tick #298 phase 4 — or record "no change".

---

## Phase 6: Measure and decide · US4 — #298 phase 5

- [ ] T015 [US4] Ten check runs in a row on a clean tree: record each run's result, the step's time and the wall time here. All green → post the comparison (the step alone and in the run, the run's wall time, against T004's baseline and #279's 85 s) on #298 when the maintainer says so, and tick phase 5. A failure → find what failed under load, and revert the phase that caused it (FR-008) before going on.

---

## Phase 7: The check run (commit 6) · #298 phase 6

- [ ] T016 Run `bash scripts/run_checks_with_log.sh` and take it to zero — only the two accepted remarks stay; prepare commit 6: `chore: take the check run to zero (#298)`. If the first run is already clean there is nothing to commit; record that here.

---

## Phase 8: Documentation (commit 7) · #298 phase 6

- [ ] T017 Update `docs/how-to/run-the-checks.md`: the longest chain and the run's time with the new numbers, and one paragraph on the layout step — its three parts, what each checks, and that they run at the same time — with the step's real output lines (the part times and the summary). No `examples/` script or notebook (as for #279). Update the Russian draft beside it. Prepare commit 7: `docs(how-to): the faster layout step (#298)`.

---

## Phase 9: Changelog (commit 8) · #298 phase 6

- [ ] T018 One article at the top of `docs/CHANGELOG.md`: the check run is shorter again, because its slowest step does its parts together — and it still checks every page in all three browsers at both sizes. Plain words, no technical detail; its Russian version in `docs/CHANGELOG.ru_draft.md`. Prepare commit 8: `docs(changelog): <title> (#298)`; tick #298 phase 6.

---

## Dependencies & Execution Order

- Phases in order 1 → 9; each of Phases 3–5 measures against the one before it, so they stay sequential.
- T002 before any change to the script.
- No commit, push, pull request or issue comment without the maintainer's word (constitution I).

## Implementation Strategy

- The result is Phases 2–6: a step that reports its parts and is faster, checking exactly as much. Each speed-up that does not pay is reverted on its own, so the result may be one, two or all three of them.
- Then the tail closes #298; the PR goes to `main`, and `main` is then brought into `feature/issue-273-graph-history`.
