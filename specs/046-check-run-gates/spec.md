# Feature Specification: Check run — Radon as a real gate, one Ruff step, package builds confirmed

**Feature Branch**: `feature/issue-296-check-run-radon-gate-ruff-builds`

**Created**: 2026-11-01

**Status**: Draft

**Input**: GitHub issue #296, "Check run: make Radon a real gate, one Ruff step, faster package builds". Phases: package builds use the fast installer with identical artifacts; Radon fails on complexity grade D or worse and on maintainability grade B or worse, with the six D-graded functions simplified or excepted by name with a reason; the duplicate Ruff lint step is dropped; closing check run, documentation, changelog. Every real check is kept, times are measured before and after, and no dependency is added.

## What changed since the issue was written

The issue predates #279 and #326. Checked against `main` at 197415c3:

- **The package builds already run through `uv build`, and only in CI.** The `python -m build` command the issue measured no longer exists in the run. The wished-for speed-up has landed, so User Story 3 proves it instead of changing it.
- **"Ruff lint" is CI's only Ruff check.** "Ruff auto-fix" runs only locally, because CI must not change the tree. Removing "Ruff lint" outright, as the issue says, would leave pull requests with no Ruff check at all. User Story 2 keeps one step that works in both places.
- **`aoa_run/` no longer exists.** Both Ruff steps now cover the same three paths: `packages/`, `tests/`, `scripts/`.
- **The six D-graded functions listed in the issue are still exactly those six** (complexity 21 to 28).
- **One module is no longer graded A.** The issue says every module is A, but `packages/maxitor/core/graph_map/tests/test_graph_map.py` is now graded B (index 11.45). With the threshold at B, the maintainability gate would fail on the day it is switched on, so this module is dealt with in the same work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A too-complex function stops the run (Priority: P1)

A developer writes a function, or lets one grow, past the complexity limit. Today the run prints it among 455 others and stays green. After this change the run fails and names the function, its file and its grade, so the problem is met when it is made.

**Why this priority**: It is the only change here that alters what the run can catch. Two steps that spend time and can never fail become real checks.

**Independent Test**: Make one function deliberately D-grade and run the check; the complexity step fails and names it. Restore; the step passes.

**Acceptance Scenarios**:

1. **Given** a function graded D or worse that is not excepted, **When** the check run reaches the complexity step, **Then** the step fails and prints the function's name, file and grade.
2. **Given** several such functions, **When** the step runs, **Then** all of them are listed, not only the first.
3. **Given** only functions graded C or better, **When** the step runs, **Then** it passes.
4. **Given** the six functions graded D on 2026-11-01, **When** this work is finished, **Then** each is graded C or better, or is excepted by name with its reason written beside the exception.
5. **Given** a module graded B or worse for maintainability, **When** the maintainability step runs, **Then** the step fails and names the module and its grade.
6. **Given** every module graded A, **When** the maintainability step runs, **Then** it passes.
7. **Given** `test_graph_map.py`, graded B on 2026-11-01, **When** this work is finished, **Then** it is graded A, or is excepted by name with its reason written beside the exception.

---

### User Story 2 - One Ruff step that means the same everywhere (Priority: P2)

A developer reading the run sees one Ruff step instead of two that cannot disagree. Locally it fixes what it can and fails on the rest. In CI it changes nothing and fails on any finding.

**Why this priority**: It makes the run easier to read and saves almost no time, so it matters less than the new gates. The risk is losing CI's Ruff check, which the scenarios below rule out.

**Independent Test**: Run the local check on an unfixable error, then on a fixable one; run the CI form on a fixable one.

**Acceptance Scenarios**:

1. **Given** an error Ruff cannot fix, **When** the local run reaches the Ruff step, **Then** the run fails.
2. **Given** an error Ruff can fix, **When** the local run reaches the Ruff step, **Then** the error is fixed and the run passes.
3. **Given** any Ruff finding, fixable or not, **When** the CI form of the run reaches the Ruff step, **Then** the step fails and no file is changed.
4. **Given** the listing of the run's steps, **When** a reader looks for Ruff, **Then** there is exactly one Ruff step, in both the local and the CI form.

---

### User Story 3 - Package builds confirmed fast and unchanged (Priority: P3)

The maintainer wants the issue's claim about builds settled with evidence, since the change it asked for has already landed in another form.

**Why this priority**: Nothing in the run changes; this closes a phase with proof.

**Independent Test**: Build every package both ways and compare the artifacts file by file, with times.

**Acceptance Scenarios**:

1. **Given** each of the eight packages, **When** it is built the way CI builds it and the way the issue measured, **Then** the wheel and the sdist contain the same files in both builds, and the time of each is recorded.
2. **Given** a difference in any artifact, **When** it is found, **Then** it is reported to the maintainer with the package and the files, not passed over.

---

### Edge Cases

- A function exactly at complexity 21 is graded D and fails; one at 20 is graded C and passes.
- An exception that names a function which no longer exists, or which is no longer D-graded, fails the step, so stale exceptions cannot pile up.
- An exception without a written reason fails the step.
- If Radon's output cannot be read, or Radon itself fails, the step fails; it never passes by reading nothing.
- Test functions count: two of the six are tests, and the step covers `packages/` including their tests, as it does today.
- A complexity failure in the run before a commit is the same failure as in the full run and in CI: the two steps keep their place in all three.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The complexity step MUST fail on any function graded D or worse (complexity 21 and above) that is not excepted.
- **FR-002**: The complexity step's failure MUST name every offending function with its file and grade.
- **FR-003**: The maintainability step MUST fail on any module graded B or worse, naming each module and its grade.
- **FR-004**: Both steps MUST keep their names ("Radon cyclomatic complexity", "Radon maintainability index") and their place in the local, the before-commit and the CI runs.
- **FR-005**: Each of the six D-graded functions MUST be simplified to grade C or better, with its behaviour unchanged, or be excepted by name with the reason beside the exception. Simplifying is the default; an exception is used only where simplifying is not reasonable.
- **FR-006**: An exception MUST be a named function or module with a reason. An exception whose target is gone or no longer over the limit, or which has no reason, MUST fail the step.
- **FR-006a**: `test_graph_map.py` MUST be brought to grade A with every assertion kept, or be excepted under FR-006.
- **FR-007**: The run MUST have exactly one Ruff step, in both its local and its CI form.
- **FR-008**: That step MUST, locally, fix what can be fixed and fail on what remains, and, in CI, fail on any finding without changing a file.
- **FR-009**: The package builds MUST stay as they are. Their identical artifacts, file by file, and their times MUST be shown for all eight packages.
- **FR-010**: Each phase's comment on the issue MUST carry the time before and after, on the same machine and tree.
- **FR-011**: Every failure mode of a new gate MUST be shown by a deliberate break that the gate catches, and no other step's result may change.
- **FR-012**: The work MUST add no new dependency and MUST NOT change what any test checks, beyond restructuring the two D-graded tests while they keep every assertion.
- **FR-013**: The pull request MUST state that "Ruff lint" left the run, so the maintainer can change the list in the constitution. The agent does not edit the constitution.
- **FR-014**: The change MUST close with the three steps of Principle VI, in order: the check run taken to zero, the documentation, the changelog as one article.

### Key Entities

- **Exception**: a function allowed to stay at grade D or worse, or a module allowed to stay at grade B or worse. It has a name, a file and a written reason.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the gates on, a function at complexity 21 or a module at grade B fails the run; both are shown by a deliberate break, then restored.
- **SC-002**: On finished work, no function is graded D or worse except those named as exceptions, and the number of exceptions is at most six, ideally zero.
- **SC-003**: A reader of the run's step list finds one Ruff step, down from two.
- **SC-004**: No real check is lost: a Ruff error still fails both the local run and CI, each shown on a deliberate error.
- **SC-005**: All eight packages show identical files in wheel and sdist between the two ways of building.
- **SC-006**: The run is green with only the two accepted remarks, and its wall time is not higher than before this work.

## Assumptions

- **The maintainability threshold is grade B or worse**, confirmed by the maintainer on 2026-11-01. One module is at B today, so that module is fixed or excepted in this work.
- Phase 1 of the issue ends with evidence in a comment and no commit of its own, because no code changes. The issue's phase list is corrected to match when the maintainer asks for it.
- The one Ruff step keeps the name "Ruff auto-fix" and its place before the steps that read the files it may rewrite.
- A D-graded test is simplified by restructuring only: every assertion stays and still fails on what it failed on before.
- Out of scope, as in the issue: parallel execution (#279), CI caching, the three-engine layout step (#298), a tool's configuration beyond the steps named here.
