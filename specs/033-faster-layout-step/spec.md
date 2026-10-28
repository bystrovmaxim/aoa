# Feature Specification: A Faster Three-Engine Layout Step That Checks Exactly as Much

**Feature Branch**: `feature/issue-298-faster-layout-step`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/298 — Check run: make the three-engine layout step faster without checking less. Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-28

- **The step sets the length of the check run.** Since #279, `bash scripts/run_checks_with_log.sh` runs independent steps at the same time and takes about 85 s on the maintainer's Apple M3 Max (14 cores). Its longest chain is the auto-fix (0.1 s), the Maxitor client build (about 22 s under load) and the step "Maxitor client: the same layout in three engines" (about 62 s). Every other step ends beside that chain; the next longest is the tests of `aoa-action-machine` under load, about 44 s.
- **What the step is.** `node scripts/check-layout-determinism.ts`, run in `packages/aoa-maxitor/client` after the client build. It serves the built client and a frozen reference graph (`packages/aoa-maxitor/tests/fixtures/ref-graph-2026-10-26.json.gz`), starts a Maxitor API on a free port, and then runs three parts, one after another:

  | Part | What it checks | How it runs today | Time, alone |
  |---|---|---|---|
  | A. Layout hashes | every page the left panel lists in every layout mode — 56 page-modes — gets the same layout hash in Chromium, Firefox and WebKit at 375×812 and at 1600×900 | the three engines at once; within each engine, the two screen sizes one after the other | 25.2 s, with starting Maxitor |
  | B. Pointer in a room | in each engine, a desktop and a phone page in one room: a resting pointer and a tap land within 2 px of the same node, before and after zooming | the three engines at once, after part A | 7.2 s |
  | C. Following | in each of the six directed pairs of engines: the follower's screen is centred on the leader's point within 2 px, the hover shows within 500 ms, the circles do not touch, the card's buttons stay inside the card | one pair after another, about 4.6 s each | 27.5 s |

  The whole step took 59.9 s alone.
- **Nothing ties the parts' order.** Each screen size of part A uses its own fresh browser context; each pair of part C opens its own new room; part B opens its own rooms; every check reads only its own pages.
- **How it reports.** One line per page-mode (`ok` with the hash, or `DIFF` with the hash of every engine and size), then one line per pointer case, then one line per following pair, then a summary line with the step's time. Exit code 1 as soon as any line is `DIFF`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowing where the step's time goes (Priority: P1)

The maintainer sees how long each part of the layout step took, besides its total, so every change to the step is judged by numbers.

**Why this priority**: Without per-part times a faster step cannot be shown, and the place to gain cannot be chosen.

**Independent Test**: Run the step alone and inside the check run; its output names the time of parts A, B and C and the total.

**Acceptance Scenarios**:

1. **Given** the step runs, **When** it ends, **Then** its output gives the time of each part and of the whole step.
2. **Given** two runs alone and one inside the check run, **When** their times are posted on #298, **Then** they are the baseline for User Story 2.
3. **Given** the timing is added, **When** the output is compared with today's, **Then** the only additions are the times.

---

### User Story 2 - A shorter wait for every check run (Priority: P1)

Everyone who finishes a change waits less, because the layout step runs at the same time what does not depend on each other — the following pairs, the two screen sizes, the pointer cases — while it checks exactly what it checks today.

**Why this priority**: This step is the longest chain of the check run; nothing else shortens the run.

**Independent Test**: Run the step and the check run on the same machine; the step and the run are faster than the baseline, and the step's output lists the same lines in the same order.

**Acceptance Scenarios**:

1. **Given** the faster step, **When** it runs, **Then** it checks the same 56 page-modes in the same three engines at the same two sizes, the same three pointer cases and the same six following pairs, with the same tolerances.
2. **Given** the faster step, **When** its output is compared with today's, **Then** it lists the same lines in the same order, apart from times.
3. **Given** each change (pairs side by side, sizes side by side, part B beside the rest), **When** it lands, **Then** the step's time before and after it is recorded, and a change that does not make the step faster is reverted.
4. **Given** the finished step, **When** the check run is timed on the baseline machine, **Then** its wall time is lower than #279's 85 s.

---

### User Story 3 - The step still catches what it catches (Priority: P1)

A faster step that let a difference through would be worse than a slow one. A layout that differs in one engine, a pointer that lands too far, and a follower that does not follow must still fail the step.

**Why this priority**: The step exists to fail on these; running parts side by side must not hide a failure.

**Independent Test**: Break each part on purpose, one at a time; each break fails the step and names what failed; restore.

**Acceptance Scenarios**:

1. **Given** a layout hash that differs in one engine and size, **When** the step runs, **Then** it fails with `DIFF` naming that page and mode and every engine's hash.
2. **Given** a pointer offset above 2 px in one engine, **When** the step runs, **Then** it fails on that pointer case.
3. **Given** a follower that ends more than 2 px from the leader's point in one pair, **When** the step runs, **Then** it fails on that pair.

---

### User Story 4 - Green every time (Priority: P2)

More browsers at once put more load on the machine. The step must stay green run after run inside the full check run, with its time limits (500 ms for a hover, 60 s for a layout) still met.

**Why this priority**: A flaky step costs more time than it saves; Story 2 ships only on top of this.

**Independent Test**: Ten check runs in a row on a clean tree are green.

**Acceptance Scenarios**:

1. **Given** ten check runs in a row on a clean tree, **When** they end, **Then** all ten are green and the step's time is recorded for each.

### Edge Cases

- A part fails while others still run: the step waits for all of them, prints every line, and exits 1.
- The Maxitor API fails to start: the step fails as today, before any part runs.
- A page-mode gives no hash in one engine or size: `DIFF` with "run(s) gave no hash", as today.
- The machine is loaded by the rest of the check run: the hover limit of 500 ms is still met; today's measured hovers are 18–45 ms.
- A pair's room: every pair still opens its own new room, so pairs running at once never share a room.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The step MUST check the same 56 page-modes in the same three engines at the same two screen sizes, the same three pointer cases and the same six following pairs, with the same tolerances (2 px; 500 ms; circles apart; buttons inside the card) and the same time limits.
- **FR-002**: The step MUST print the time of parts A, B and C and of the whole step.
- **FR-003**: Apart from times, the step's output MUST list the same lines in the same order as today: page-modes in the left panel's order, pointer cases in engine order, following pairs in today's pair order.
- **FR-004**: The six following pairs MUST run at the same time, each in its own new room.
- **FR-005**: In part A, each engine MUST lay out both screen sizes at the same time, each in its own fresh browser context.
- **FR-006**: Part B MUST NOT wait for part A to end.
- **FR-007**: Any `DIFF` in any part MUST make the step exit 1, after every part has ended and printed its lines.
- **FR-008**: Each of FR-004, FR-005 and FR-006 MUST be measured before and after it lands, and MUST be reverted if it does not make the step faster or if it makes the step fail where it passed.
- **FR-009**: Ten check runs in a row on a clean tree MUST be green before the change ships.
- **FR-010**: Only the step's script changes; Maxitor, its client and its tests do not.
- **FR-011**: The change MUST end with the check run taken to zero, the documentation and the changelog, in that order (Principle VI); the documentation is the how-to page of the check run, whose description of the longest chain is updated.

### Key Entities

- **Part**: one of the step's three checks — layout hashes, pointer in a room, following — with its time.
- **Pair**: a leading engine and a following engine in one room; six directed pairs.
- **Baseline**: the step's per-part and total times, alone and inside the check run, before any change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The step reports the time of each of its three parts and its total in 100 % of runs.
- **SC-002**: The step alone is faster than its baseline of 59.9 s on the same machine, and the check run's wall time is lower than 85 s; both numbers are posted on #298.
- **SC-003**: The step's output, with times removed, is identical to today's.
- **SC-004**: Each of the three deliberate breaks fails the step and names what failed.
- **SC-005**: Ten check runs in a row on a clean tree are green.

## Assumptions

- The machine for every measurement is the maintainer's Apple M3 Max with 14 cores, as for #279.
- How much the step gains depends on how well the machine carries more browsers at once; the estimate (the step about 15–25 s, the check run about 50 s) is checked by measurement, not assumed.
- The deliberate breaks of User Story 3 are made in the step's own comparison inputs (one engine's hash, one pointer offset, one follower's distance), because Maxitor itself is outside this change (FR-010).
- Running the step only when certain files change is out of scope (#298 §7).
