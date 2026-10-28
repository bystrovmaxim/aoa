# Feature Specification: A Check Run That Measures Itself and Runs Independent Steps Together

**Feature Branch**: `feature/issue-279-parallel-checks`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/279 — Check run: measure every step, then run independent checks in parallel. Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-28

- **The check run is the gate of every change.** No change in this repository is finished until `bash scripts/run_checks_with_log.sh` runs clean (constitution, Principle VI). Its log, `archive/logs/check-all.txt`, is what the maintainer and the agent read afterwards.
- **37 steps, one after another.** In order:
  - 2 shell guards: no `__getattr__` in a package `__init__.py`, and a README beside every client component;
  - 8 Maxitor client steps: install and build, unit tests, the three-engine layout step of #271 (already present), and five ERD scripts;
  - `ruff check --fix`, which **rewrites Python files**;
  - Ruff lint, mypy, pylint, package boundaries and package metadata;
  - 8 wheel/sdist builds, one per package, followed by the packaging smoke test that installs every built wheel;
  - vulture and the samples public-API check;
  - pytest, once per package (8 runs; one combined run fails at collection, because every package names its test package `tests`);
  - Radon complexity and Radon maintainability.
- **The run takes the sum of its steps.** The last full run, on an Apple M3 Max with 14 cores and 36 GB, took **3 min 41 s** (10:59:55 → 11:03:36). Neither the log nor the console records how long each step took, so which steps are slow is unknown.
- **What depends on what.** Every Python step reads files that `ruff --fix` may rewrite. The client steps after the build use what the build wrote to `packages/aoa-maxitor/client/dist`. Each package build writes its own `packages/<pkg>/dist`, and the packaging smoke test reads all of them. The Maxitor sdist packs the `client/` folder, including `client/dist` — so the Maxitor package must not be built while the client is being built. The layout step starts its own API on a free port, so it shares no fixed port with the tests.
- **How the log reads.** The log has a header, then one block per step: `=== <name> ===`, `$ <command>`, the full output, `OK <name> (exit 0)` or `FAIL <name> (exit N)`, then a footer. The console prints `> <name>` when a step starts and `OK`/`FAIL` when it ends. The script exits non-zero if any step failed, and a failing step does not stop the run.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowing what the run spends its time on (Priority: P1)

The maintainer runs the checks and sees how long each step took, and how long the whole run took, both on the console and in the log. Before anything about the order changes, two runs on a clean tree give a baseline that every later change is compared against.

**Why this priority**: Any speed-up has to be shown by numbers, and without per-step times nobody knows which steps are worth running together. It is also useful on its own: a step that suddenly takes twice as long is visible at once.

**Independent Test**: Run the check script on a clean tree; every step's line on the console and in the log shows its duration, and the run ends with the total wall time.

**Acceptance Scenarios**:

1. **Given** a clean tree, **When** the check run finishes, **Then** every one of the 37 steps shows its duration on the console and in the log, and the run ends by printing its total wall time.
2. **Given** two runs on the same clean tree, **When** their times are posted on #279, **Then** they form the baseline used by User Story 3.
3. **Given** the timing is added, **When** the log is compared with a log from before it, **Then** the only difference is the added times.

---

### User Story 2 - A log that reads the same, whatever runs at the same time (Priority: P1)

Whoever reads `check-all.txt` after a run — the maintainer, or the agent looking for a failure — finds every step in the same fixed order as today, each with its command, its duration, its complete output and its `OK`/`FAIL` line. The output of two steps is never mixed, even when they ran at the same moment.

**Why this priority**: The log is how a failure is found and read. A faster run whose log interleaves eight test outputs would cost more time than it saves.

**Independent Test**: Run the checks with the steps writing to separate places and joined at the end; compare the order and content of the log with a run from before.

**Acceptance Scenarios**:

1. **Given** any run, **When** it finishes, **Then** `check-all.txt` lists all 37 steps in today's order, each with its command, its duration, its full output and its `OK`/`FAIL` line.
2. **Given** steps that ran at the same moment, **When** the log is read, **Then** no line of one step's output appears inside another step's block.
3. **Given** the change that separates the outputs is made while the run is still sequential, **When** its log is compared with the log before it, **Then** they read the same apart from the times.

---

### User Story 3 - A faster run that checks exactly the same things (Priority: P2)

The maintainer starts the check run and waits less, because steps that do not depend on each other run at the same time. Nothing that was checked before goes unchecked, a failure is reported exactly as before, and the machine stays usable.

**Why this priority**: This is the point of the issue, but it rests on Stories 1 and 2: without the times it cannot be shown to be faster, and without the separate outputs its log could not be read.

**Independent Test**: Run the parallel script twice on the same clean tree and machine as the baseline; it is green, its wall time is lower, and its log matches the sequential one in order and content.

**Acceptance Scenarios**:

1. **Given** the parallel run, **When** it is compared with the baseline on the same tree and machine, **Then** its wall time is lower, and both numbers are in the pull request.
2. **Given** the parallel run, **When** it starts, **Then** the two shell guards and `ruff check --fix` finish before any other Python step starts.
3. **Given** the parallel run, **When** it runs, **Then** no client step that uses the client build starts before the build has finished, the packaging smoke test starts only after every package build has finished, and the Maxitor package build does not overlap the client build.
4. **Given** one broken step in each group — a failing client test, a mypy error, a broken package build, a failing test in one package — **When** the run finishes, **Then** exactly those steps are marked `FAIL`, every other step still ran and reported, and the exit code is non-zero. Each break is restored afterwards.
5. **Given** a limit of how many steps may run at once, **When** it is set to 1, **Then** the run is sequential and its log is the same as with any other limit, apart from the times.
6. **Given** a running check run, **When** the maintainer interrupts it (Ctrl+C), **Then** every running step stops and nothing keeps running in the background.

---

### User Story 4 - Tests that pass whether they run alone or together (Priority: P2)

Running the eight test suites at the same moment must not make any test fail that passes alone — through a fixed port, a shared temporary file, a shared database or a time limit a loaded machine misses. Such a test is fixed, not hidden.

**Why this priority**: A parallel run that is red one time in five is worse than a slow one; Story 3 can only ship on top of this.

**Independent Test**: Run the eight test suites in parallel ten times in a row on a clean tree; all ten are green.

**Acceptance Scenarios**:

1. **Given** the eight test suites running at the same time, **When** this is repeated ten times on a clean tree, **Then** all ten runs are green.
2. **Given** a test that fails only when run beside others, **When** it is found, **Then** the test is fixed so that it no longer shares anything with other suites.
3. **Given** a test that cannot be fixed within this issue, **When** the run is scheduled, **Then** its package's suite runs alone, and the reason is written next to that decision in the script.

### Edge Cases

- A step that cannot start at all (a missing tool): it is reported `FAIL` like any failing step, and the run continues.
- A step that prints nothing: its block still appears in its place, with its command, its duration and its `OK`/`FAIL` line.
- `ruff check --fix` changes files: every later Python step sees the changed files, as today.
- A run interrupted halfway: no step keeps running, and the log written so far is not presented as a finished run.
- A limit that is not a positive whole number: the run says so and stops before starting any step.
- Two check runs started at the same time in one checkout: not supported, as today; one log file is shared.
- The parallel run is not faster on the baseline machine: it is not shipped (User Story 3 fails), and the pull request says what stood in the way.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every step that runs today MUST still run, with the same command; this work MUST NOT add a check or remove one.
- **FR-002**: Every step's duration MUST be shown on the console when it finishes and written into its block in the log; the run MUST end by showing its total wall time.
- **FR-003**: The log MUST list all steps in today's fixed order, each with its command, its duration, its complete output and its `OK`/`FAIL` line, with the same header and footer as today.
- **FR-004**: The output of different steps MUST never be interleaved in the log, whichever steps ran at the same time.
- **FR-005**: The two shell guards and `ruff check --fix` MUST finish before any other Python step starts.
- **FR-006**: Steps MUST run at the same time only where neither depends on the other: the client steps after the client build; the packaging smoke test after every package build; the Maxitor package build never during the client build. Steps that read only MAY run alongside each other.
- **FR-007**: The tests MUST still run as one run per package.
- **FR-008**: The number of steps running at once MUST be limited; by default the limit is the machine's number of cores, it MUST be changeable without editing the script, and a limit of 1 MUST give a sequential run with the same log.
- **FR-009**: A failing step MUST NOT stop the others; each failure MUST be marked `FAIL` on the console and in the log, and the run MUST exit non-zero if any step failed and zero otherwise.
- **FR-010**: Interrupting the run MUST stop every running step and leave no process behind.
- **FR-011**: No test may fail only because other test suites run at the same time; a test that does MUST be fixed, or its package's suite MUST run alone with the reason written in the script.
- **FR-012**: The parallel run MUST ship only if two runs are green and faster than the baseline on the same tree and machine; otherwise the measurement and timing (FR-002, FR-003, FR-004) ship alone, and the pull request says what stood in the way.
- **FR-013**: The two accepted remarks — the Vite chunk-size advisory and LangGraph's pending-deprecation warning — MUST stay in the log as today.
- **FR-014**: The change MUST end with the check run taken to zero, the documentation and the changelog, in that order (Principle VI); the documentation says how the run is ordered, what the limit is and how to change it, and how to read the log.

### Key Entities

- **Step**: one command the run executes, with a fixed name, a fixed place in the log, a duration and an outcome (`OK` or `FAIL` with its exit code).
- **Group**: steps that must keep an order among themselves but may run beside other groups — the guards and auto-fix, the client, static analysis, packaging, tests.
- **Limit**: how many steps may run at the same moment.
- **Baseline**: per-step and total times of two sequential runs on a clean tree, against which the parallel run is judged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of the 37 steps show their duration on the console and in the log, and every run reports its total wall time.
- **SC-002**: The parallel run's wall time is lower than the baseline's on the same tree and machine (baseline today: 3 min 41 s on the M3 Max); both numbers are posted on #279 and in the pull request.
- **SC-003**: Ten parallel runs in a row on a clean tree are all green.
- **SC-004**: Breaking one step in each group makes exactly those steps `FAIL`; every other step still reports.
- **SC-005**: A run with a limit of 1 and a run with the default limit produce logs that are the same apart from times.
- **SC-006**: In every log of a parallel run, each step's block holds only that step's output.

## Assumptions

- The baseline and the comparison are measured on the maintainer's machine (Apple M3 Max, 14 cores, 36 GB); other machines may gain more or less.
- The default limit equals the number of cores; whether that overloads the machine is learned from the measurements of User Story 1 and adjusted then, not guessed now.
- The run stays one shell script driven from the repository root; continuous integration, caching between runs and running only what a change touches are out of scope, as #279 says.
- Steps that share the project's Python environment may wait for each other while it is being prepared; this is accepted, not avoided.
- What each step checks, and every tool's configuration, stay as they are.
