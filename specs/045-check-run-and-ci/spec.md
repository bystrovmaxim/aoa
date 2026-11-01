# Feature Specification: Check run and CI — decide what runs where

**Feature Branch**: `feature/issue-326-check-run-and-ci`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Check run and CI: decide what runs where, and stop the local run depending on PyPI" (issue #326)

## User Scenarios & Testing *(mandatory)*

The actors are the **maintainer** (who runs the local check run before a merge), a **contributor** (who opens a pull request and reads its CI result), and the **release process** (which publishes packages from tags).

### User Story 1 - A pull request gets a meaningful CI result (Priority: P1)

A contributor opens a pull request and CI runs the real checks and tests, so a result appears that does not depend on the maintainer's computer. Today CI builds the Maxitor client, checks the graph files and the branch name, and runs no tests, so a pull request can be merged with no test having run outside one computer.

**Why this priority**: This is the core defect — the gate is almost empty. Without it the other moves have no teeth.

**Independent Test**: Open a pull request with a change that fails an ordinary unit test; CI must fail that pull request, on its own machine.

**Acceptance Scenarios**:

1. **Given** a pull request that breaks a package's unit test, **When** CI runs, **Then** the pull request is reported failing, independent of any local machine.
2. **Given** a pull request that passes all ordinary tests but violates a static check (e.g. lint or typecheck), **When** CI runs, **Then** the pull request is reported failing.

---

### User Story 2 - The local run finishes with no network (Priority: P1)

The maintainer runs `bash scripts/run_checks_with_log.sh` with the network off and, once the tools are installed, the run reaches zero remarks without waiting on pypi.org. Today the `Build wheel/sdist` step downloads the build tool on every run and fails on a poor connection, and the packaging smoke step installs dependencies over the network.

**Why this priority**: This is the second named defect — the local run depends on a network it should not need.

**Independent Test**: Disable the network and run the local check; it completes with zero remarks.

**Acceptance Scenarios**:

1. **Given** the network is off and the tools are installed, **When** the maintainer runs the local check, **Then** it ends at zero remarks.
2. **Given** the network is off, **When** the local check runs, **Then** no step waits on a download from pypi.org.

---

### User Story 3 - A broken package is caught before release (Priority: P2)

A broken wheel or sdist definition is caught before the package is published. The local run no longer builds the packages, so the build must happen somewhere that runs before a release.

**Why this priority**: The build exists to catch broken packages; it matters at release time, not on every local run.

**Independent Test**: Break one package's build definition and open a pull request; CI must fail. The same break must be impossible to release.

**Acceptance Scenarios**:

1. **Given** a pull request with a broken package definition, **When** CI runs, **Then** the build step fails the pull request.
2. **Given** a tag that triggers publishing, **When** the package builds, **Then** a broken definition fails the publish.

---

### User Story 4 - Every check has one stated home (Priority: P2)

Every step of the check run has exactly one stated home — the local run, CI, or both — written in the documentation, with a reason. Nobody has to guess where a check belongs.

**Why this priority**: The issue's root cause is that nobody ever decided which check belongs where; the decision must be written down.

**Independent Test**: Read the decision table; every step of the local run appears exactly once, with a home and a reason.

**Acceptance Scenarios**:

1. **Given** the decision is recorded, **When** a reader asks where a step runs, **Then** the answer is in one table with a reason.

---

### User Story 5 - Graph files are always written or checked (Priority: P2)

The repository's graph files are always written or checked: a failure in an unrelated step can never leave them neither written nor checked. Today the graph step runs only when every other step passed, so one failure skips it entirely.

**Why this priority**: This is a stated acceptance criterion and a correctness guarantee about the graph files.

**Independent Test**: Force an unrelated step to fail and run the check; the graph files must still be checked (or written on a green run).

**Acceptance Scenarios**:

1. **Given** the run is green, **When** the graph step runs, **Then** the graph files are written.
2. **Given** an unrelated step failed, **When** the run ends, **Then** the graph files are still checked, not silently skipped.

---

### User Story 6 - Speed tests do not fail on a busy machine (Priority: P3)

Benchmark and timing tests do not fail merely because the machine is busy. They still run somewhere, but a busy machine cannot turn a correct change into a failed check.

**Why this priority**: These tests already flake; making them safe is a smaller correctness fix than the gates above.

**Independent Test**: Run the speed tests on a loaded machine; they pass or are clearly excluded from the path that must be green.

**Acceptance Scenarios**:

1. **Given** a loaded machine, **When** the fast gate runs, **Then** the speed tests are not part of it.
2. **Given** the full run, **When** the speed tests run, **Then** they fail only on a real regression, not on machine noise.

---

### User Story 7 - Small changes get a fast mode (Priority: P2)

The maintainer makes a small change and does not have to pay for the whole full run. The local run offers an opt-in fast mode that runs the cheap deterministic steps — the guards, the linters and type checkers, and the Python tests — and skips the client build and unit tests, the ERD scripts, the three-engine job, the package build, the install smoke and the graph write. The full run stays the default, and CI always runs the full gate.

**Why this priority**: The maintainer asked for it directly: do not run everything on every small change, but run everything in full before a pull request.

**Independent Test**: Run the fast mode on a small Python change; it finishes without touching the client, the browsers or the package build.

**Acceptance Scenarios**:

1. **Given** the fast mode, **When** it runs, **Then** it runs the cheap deterministic steps and skips the heavy ones.
2. **Given** no flag, **When** the local check runs, **Then** it still runs the full set.

---

### User Story 8 - The browser check is proven on the commit that merges (Priority: P1)

The maintainer changed Q3: the three-engine layout stays on the maintainer's machine, and CI checks that it happened. A full local run on one commit leaves a receipt; before a pull request the maintainer reports it to GitHub as a commit status; CI fails a pull request whose commit does not carry that status. A new commit has no status of its own, so nothing merges unproved.

**Why this priority**: A CI machine has no graphics card, so Firefox has no WebGL and the map cannot be drawn; forcing a software renderer under a virtual screen passed the layout hashes but gave 30 differences in 240 on following and frames, in a configuration no user has. Run locally the check is real, and with this story it is also controlled.

**Independent Test**: Open a pull request from a commit that never had a full local run; the job `Proof of the local run` must fail, and pass once `bash scripts/check_before_pr.sh` has run on that commit.

**Acceptance Scenarios**:

1. **Given** a green full run with the tree one commit from start to end, **When** the run ends, **Then** a receipt names that commit.
2. **Given** the tree was dirty at the start, was changed during the run, or moved to another commit, **When** the run ends, **Then** no receipt is left.
3. **Given** a receipt for another commit, or uncommitted changes, **When** the sign-off is asked for, **Then** it refuses and GitHub is not called.
4. **Given** a pull request whose commit carries no status, **When** CI waits and none comes, **Then** the job fails and says what to run.
5. **Given** a commit pushed to an open pull request, **When** its full run ends within the wait, **Then** the job passes without being re-run.

---

### User Story 9 - Two scripts, named for when they run (Priority: P2)

The maintainer asked for two scripts and a rule in the constitution: `scripts/check_before_commit.sh` during the work and before every commit, and `scripts/check_before_pr.sh` before a pull request, and no pull request is opened until it has passed.

**Why this priority**: Nobody should have to remember flags to know which run a moment needs.

**Independent Test**: Run each script: the first runs the fast mode; the second refuses a dirty or unpushed tree before spending the run, then runs the full gate and signs off.

**Acceptance Scenarios**:

1. **Given** the work in progress, **When** `check_before_commit.sh` runs, **Then** it runs the fast mode.
2. **Given** a pushed commit, **When** `check_before_pr.sh` runs, **Then** it runs the full gate and, on green, signs off.
3. **Given** a red full run, **When** the script ends, **Then** nothing is reported to GitHub.

---

### Edge Cases

- **Network off during the local run**: the run must not depend on pypi.org; tool caches satisfy the build and install.
- **Poor connection in CI**: the package build uses uv's cache, so a flaky network does not fail an unrelated change.
- **Busy machine during speed tests**: timing budgets must leave headroom or the tests must be outside the fast gate.
- **An unrelated step fails before the graph step**: the graph files are still checked, never skipped.
- **A pull request opened directly from `main`**: already rejected by CI; unchanged by this work.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every step of the check run MUST have exactly one stated home — the local run, CI, or both — and that home MUST be written in the documentation with a reason.
- **FR-002**: The local check run MUST complete with zero remarks with the network off, once its tools are installed; no step of it MAY depend on pypi.org.
- **FR-003**: CI MUST run, on every pull request, the checks and tests that need no browser engine and no unusually powerful machine, and its result MUST NOT depend on the maintainer's computer.
- **FR-004**: A broken wheel or sdist definition MUST be caught before the package is released.
- **FR-005**: The packaging install smoke test MUST run wherever the archives are built, because it installs them with their dependencies.
- **FR-006**: The browser-engine layout check (three engines) MUST run in the full local run and MUST NOT run in CI; CI MUST instead fail a pull request whose commit does not carry the proof of a full local run (FR-010).
- **FR-007**: Machine-speed-sensitive tests (benchmarks and timing tests) MUST be marked as such and MUST be excluded from the fast CI path; they MUST still run in the full local run.
- **FR-008**: The graph files MUST always be written or checked; no failure in an unrelated step MAY leave them neither written nor checked, and a stale file MUST be rewritten on a green run instead of failing it.
- **FR-009**: The local run MUST offer an opt-in fast mode that runs only the cheap deterministic steps, without the speed tests, and skips the client build, the client unit tests, the ERD scripts, the three-engine check, the package build, the install smoke and the graph rows; the full run MUST stay the default.
- **FR-010**: A green full local run on one commit MUST leave a receipt naming it; `--sign-off` MUST report that receipt to GitHub as the commit status `Local check run` and MUST refuse for any tree that is not that commit; the local run itself MUST stay free of the network.
- **FR-011**: The repository MUST offer `scripts/check_before_commit.sh` (the fast mode) and `scripts/check_before_pr.sh` (the full run on a pushed commit, then the sign-off); no pull request is opened until the second has passed.

### Key Entities

- **Check step**: a named action of the check run (e.g. a static check, a test suite, a package build), characterized by its declared home and the reason for that home.
- **Home**: the place a check step runs — the local run, CI, or both.
- **Test category**: a grouping used to decide a home — static, unit, browser, package, benchmark.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the network off, the local run ends at zero remarks once its tools are installed.
- **SC-002**: A failed package build is still caught before a package is released.
- **SC-003**: Every step has one stated home, written in the documentation.
- **SC-004**: A pull request gets a result from CI that does not depend on the maintainer's computer.
- **SC-005**: The graph files are always written or checked: no failure in an unrelated step can skip them.
- **SC-006**: The fast mode runs only the cheap deterministic steps, and the full run stays the default.
- **SC-007**: A pull request whose commit never had a full local run fails in CI.

## Decision Table

The decision of phase 1: every step of today's local run, with its home and the reason. "Local" is `scripts/run_checks_with_log.sh`; "CI" is `.github/workflows/ci.yml`.

| Step | Local run | CI | Why |
|---|---|---|---|
| Ban `__getattr__` in package `__init__.py` | ✅ | ✅ | cheap shell guard, no network or browser |
| Maxitor client: README beside `components/*/index.ts` | ✅ | ✅ | cheap shell guard |
| Ruff auto-fix (`ruff check --fix`) | ✅ | — | mutates files; CI must not rewrite the tree |
| Ruff lint | ✅ | ✅ | deterministic static check |
| Mypy typecheck | ✅ | ✅ | deterministic static check |
| Pylint | ✅ | ✅ | deterministic static check |
| Package import boundaries | ✅ | ✅ | deterministic static check |
| Package metadata (dependency matrix) | ✅ | ✅ | deterministic static check |
| Vulture dead code | ✅ | ✅ | deterministic static check |
| Maxitor samples: public API | ✅ | ✅ | deterministic static check |
| Radon cyclomatic complexity | ✅ | ✅ | deterministic static check |
| Radon maintainability index | ✅ | ✅ | deterministic static check |
| Maxitor client: `npm ci` and Vite build | ✅ | ✅ | CI already builds; local needs it for the client tests |
| Maxitor client: unit tests (vitest) | ✅ | ✅ | jsdom, no browser engine |
| Maxitor client: three-engine layout | ✅ | — (its proof is read: `Proof of the local run`) | needs a graphics card: a CI machine has none, so Firefox has no WebGL there |
| Maxitor client: ERD scripts (5×, Graphviz WASM) | ✅ | ✅ | deterministic, no browser engine |
| Pytest — 12 package dirs (minus benchmarks) | ✅ | ✅ | deterministic unit/integration, no network |
| Pytest — `tests/scripts` | ✅ | ✅ | deterministic |
| Speed-sensitive tests (marked `benchmark`) | run inside the package suites | dropped by `-m "not benchmark"` | flake on a busy machine |
| Build wheel/sdist ×8 | — | ✅ | downloads the build tool; a broken build is a release concern |
| Packaging wheel install smoke | — | ✅ | installs archives with dependencies, needs network |
| Graph files: write | ✅ (green-only, before the check) | — | writes files into the commit |
| Graph files: check | ✅ (always, after the write) | ✅ | always verified, never skipped |

The **fast mode** is a local-only selector over this table: it runs the guards, the static checks and the Python tests (minus benchmarks) and skips every row marked "client", "packaging" or "graphs". It changes no step's home; the Python suites run as in CI, without the speed tests, because the mode is deterministic.

## Assumptions

- The five decisions reached in discussion are adopted as the working decision, subject to the maintainer's review of this spec: the three-engine layout stays in the full local run and CI reads its proof (the maintainer's change of Q3, after the first answer proved impossible on a machine with no graphics card); `Build wheel/sdist` and `Packaging wheel install smoke` move out of the local run into CI; the speed-sensitive tests are marked `benchmark` (the four wholly-speed files at module level, the rate-limit test in `test_websocket_route.py` individually) and excluded from the fast CI path; the graph step splits into an always-run `check` and a green-only `write`; the local run gains an opt-in fast mode that skips the heavy rows.
- The publish workflow (`.github/workflows/publish.yml`) is unchanged; it rebuilds and publishes from tags.
- Out of scope: publishing packages, version bumps and tags; making steps faster for its own sake (#296, #299).
- The constitution's "Final step: the check run" section is amended if this decision changes what the local run does; the agent drafts the wording and the maintainer ratifies it.
