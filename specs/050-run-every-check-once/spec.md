# Feature Specification: Run every check once

**Feature Branch**: `feature/issue-351-run-every-check-once`

**Created**: 2026-11-02

**Status**: Draft

**Input**: GitHub issue #351: during the work a developer runs only the tests of the current phase; CI runs the closing check run; the local machine runs only the browser tests and leaves its proof on the commit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Close a change without a local run (Priority: P1)

A developer finishes a change. During the work they ran only the tests of each phase. They push, open a pull request, and CI gives the closing verdict on the guards, the static checks and the Python tests.

**Why this priority**: This is the point of the work: the same check never runs twice for one change.

**Independent Test**: Follow the documented flow for a change and confirm no step asks the developer to run a check that CI also runs.

**Acceptance Scenarios**:

1. **Given** a finished change, **When** the developer follows the project's rules, **Then** the only local checks are the tests of each phase and the browser run.
2. **Given** a pushed change with a failing Python test, **When** a pull request is open, **Then** CI reports the failure and the merge is blocked.

---

### User Story 2 - Prove the browser run on the commit (Priority: P1)

The browser checks cannot run in CI. The developer runs them on the pushed commit, and the proof lands on that commit, whether the pull request is already open or not.

**Why this priority**: Without this, removing the local run would leave the browser layout unchecked.

**Independent Test**: Open a pull request for a commit without proof, confirm the merge is blocked, run the browser check, and confirm the merge is allowed once CI is green.

**Acceptance Scenarios**:

1. **Given** an open pull request whose commit has no proof, **When** the merge rule is evaluated, **Then** the merge is blocked.
2. **Given** that pull request, **When** the browser run passes on that commit, **Then** the proof requirement is met without a new commit.
3. **Given** a commit with proof, **When** a new commit is pushed, **Then** the new commit has no proof and the merge is blocked again.

---

### User Story 3 - Run everything on demand (Priority: P2)

A developer who wants to see every check on one machine can still run the full run. Nothing requires it.

**Why this priority**: It is a convenience for investigating failures, not part of the normal flow.

**Independent Test**: Run the full run and confirm it completes; confirm no rule requires it.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the developer starts the full run, **Then** all local steps run as a single command.

---

### Edge Cases

- The browser run starts on a tree with uncommitted changes or an unpushed commit: it refuses before spending the run.
- The browser run fails: no proof is left and the merge stays blocked.
- CI fails after the proof is on the commit: the merge stays blocked until a new commit, which needs its own proof.
- The proof status arrives after CI finished: the pull request can pass without a new commit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST NOT contain a separate script for a local closing run.
- **FR-002**: The project's rules MUST name CI as the place of the closing check run.
- **FR-003**: The project's rules MUST limit routine local checks to the tests of the current phase and the browser run.
- **FR-004**: A pull request MUST be allowed to open before the browser run has finished.
- **FR-005**: Merging MUST require a green CI and the browser proof on the exact commit being merged.
- **FR-006**: A proof that arrives after CI finished MUST count without a new commit.
- **FR-007**: The browser run MUST keep refusing a tree that is not a pushed commit.
- **FR-008**: The full run MUST remain available as one command.
- **FR-009**: The documentation MUST show what runs where, with real output.
- **FR-010**: The tail of a change MUST keep its order: closing check run at zero, documentation, changelog.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For one change, zero checks run both locally and in CI unless a developer asks for the full run.
- **SC-002**: 100% of commits without the browser proof are refused at merge.
- **SC-003**: 100% of commits with a failing CI check are refused at merge.
- **SC-004**: No project rule, plan template or skill names the removed script.

## Assumptions

- Remarks that CI's closing run reports are fixed in the change, as a local closing run's would be.
- Fixes the run's auto-fix step would make locally are made by the developer, because CI does not commit.
- The maintainer updates the constitution before the first phase is merged; agents do not edit it.
- Past specs and past changelog articles are history and keep naming the removed script.
- Moving the browser checks to CI, and a self-hosted runner, are out of scope.
