# Feature Specification: A graph's history joined with its version file

**Feature Branch**: `feature/issue-344-graph-history-version-file`

**Created**: 2026-11-02

**Status**: Draft

**Input**: GitHub issue #344, "Versioning 3/5: repo-graph-port joins a graph's history with its version file". The issue is part of #340, and #345 builds on the answer this feature gives.

## What was checked before writing this

Against `main` at b83eed70, on a clean export:

```text
cache after saving A then B at one commit: b'graph-B'
```

Two graphs of one repository at one commit share one place in the port's cache, so the second overwrites the first. Today a history is one graph file on one branch, and only commits that changed that file are versions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where the version changed without the graph (Priority: P1)

A person reading a graph's history in Maxitor needs to see every step of the version it belongs to, not only the steps that changed the graph. A history names a second file, the one that holds the version, and each point says whether the graph changed, which version is in force, and whether that version changed there.

**Why this priority**: This is the feature. Everything else protects it.

**Independent Test**: A small real git repository with a graph and a version file, with one commit changing both, one changing only the version and one changing neither. Read its history.

**Acceptance Scenarios**:

1. **Given** a commit that changed the graph and raised the version, **When** the history is read, **Then** the point says `graph_changed` yes, `version` the new number, `version_changed` yes.
2. **Given** a commit that raised the version and left the graph, **When** the history is read, **Then** it is a point with `graph_changed` no, the new number, `version_changed` yes.
3. **Given** a commit that changed the graph and kept the number, **When** the history is read, **Then** the point says `graph_changed` yes, the same number, `version_changed` no.
4. **Given** a commit that touched the version file but kept the number, such as a comment in `version.toml` or a dependency in `pyproject.toml`, and did not change the graph, **When** the history is read, **Then** it is not a point.
5. **Given** a history with no version file, **When** it is read, **Then** its points are the ones it has today, each with `graph_changed` yes, an empty `version` and `version_changed` no.

---

### User Story 2 - Name the version of any level (Priority: P1)

A graph belongs to a component or to a whole package, as in `aoa-demo`. The person configuring a history names the file and, when needed, the key that hold the number.

**Why this priority**: Without it, the graph of a package has no version to show.

**Independent Test**: One history on a `version.toml` with the default key, one on a `pyproject.toml` with `project.version`, and one public link given both parameters.

**Acceptance Scenarios**:

1. **Given** `version_file` naming a `version.toml`, **When** the history is read, **Then** numbers come from its `version`.
2. **Given** `version_file` naming `pyproject.toml` and `version_key = "project.version"`, **When** the history is read, **Then** numbers come from that key at each commit.
3. **Given** a JSON version file, **When** the history is read, **Then** the key is read the same way.
4. **Given** a public link with `version_link` and `version_key`, **When** it is read, **Then** it behaves as a configured history does.

---

### User Story 3 - A bad link never takes the graph away (Priority: P1)

A wrong path, a missing key or a broken file must be explained in plain words, and the graph must stay open.

**Why this priority**: The config lives on the server, so a folder moved in a pull request leaves it behind. That must not cost anyone the history, or any other history in the file.

**Independent Test**: Each broken link in turn, reading both the history answer and the versions answer.

**Acceptance Scenarios**:

1. **Given** a version file that is not above the graph, or is missing at the head of the branch, **When** the history is read, **Then** `version_problem` says so in plain text and the graph opens.
2. **Given** a missing key, a value that is not a string, a broken file or a file in another format at the head, **When** the history is read, **Then** `version_problem` names the cause.
3. **Given** a `version.toml` with `driver` instead of `version`, **When** the history is read, **Then** `version_problem` names the file to link to instead.
4. **Given** a bad link, **When** Maxitor polls only the versions answer, **Then** it still receives `version_problem`.

---

### User Story 4 - Two graphs in one repository stay apart (Priority: P1)

A component may hold several graphs, and one commit may change more than one.

**Why this priority**: The cache already mixes them up, and more points make it happen more often.

**Independent Test**: Read two graphs of one repository at the same commit, in both orders, cold and warm.

**Acceptance Scenarios**:

1. **Given** two histories on different graph files at one commit, **When** both are read, **Then** each gets its own bytes, facts and detail.
2. **Given** a cache written by the old version, **When** the new version starts, **Then** nothing old is served as if it were correct.

---

### User Story 5 - A moved folder keeps its history (Priority: P2)

Folders do move: `src` left Maxitor in #341. The person configuring a history lists the old paths, and the history before the move stays.

**Why this priority**: Without it, a move loses history, but only for the histories that moved.

**Independent Test**: A repository whose graph and version file moved mid-history, configured with `graph_file_before` and `version_file_before`.

**Acceptance Scenarios**:

1. **Given** old paths in the config, **When** the history is read, **Then** each commit is read from whichever path exists there.
2. **Given** no old paths, **When** the history is read, **Then** it starts at the current path, as today.

### Edge Cases

- The version file appears later than the graph: earlier points have an empty `version`, and the first readable number counts as a change.
- The file is broken, then fixed: a broken commit is a point only if the graph changed, with an empty `version`. The fix is a change only if the number differs from the last readable one.
- The number goes down: `version_changed` is yes. The port reports what it sees, and judging is the job of CI.
- The file is deleted: an empty `version`, and `version_problem` if it is gone at the head.
- The graph is deleted: a point with `refused`, as today. Restoring it is the next point.
- Only the formatting of the graph changed, or a file is not JSON: formatting and the order of top-level nodes and edges are not a change; a file that is not JSON is compared by its bytes.
- A computed version (`dynamic = ["version"]`, `version.workspace = true`): the port does not resolve it and reports it. Rust can name `workspace.package.version` in the root `Cargo.toml`.
- Commits before the graph existed are not points: they have no graph to open.
- Open pull requests stay as they are today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A history MUST be able to name `version_file` and an optional `version_key`, in the histories config, and as `version_link` and `version_key` on a public link.
- **FR-002**: With no version file, a history MUST answer as it does today, plus the three fields with their neutral values.
- **FR-003**: The port MUST read one key, `version` by default, from a TOML or JSON file chosen by its extension, at each commit. It MUST NOT need drivers or the version tool.
- **FR-004**: A commit that changed either file MUST become a point only if `graph_changed` or `version_changed` is true.
- **FR-005**: `graph_changed` MUST mean the graph document differs from the previous point's, ignoring formatting and the order of top-level nodes and edges.
- **FR-006**: `version` MUST be the number in the file at that commit, or empty when the file is missing or cannot be read. Maxitor MUST NOT have to work it out from other points.
- **FR-007**: `version_changed` MUST mean the number differs from the last readable number before it. The first readable number counts as a change.
- **FR-008**: The list MUST start at the first commit that has the graph file.
- **FR-009**: The folder of `version_file` MUST contain `graph_file`, and both MUST exist at the head of the branch, or the answer MUST carry `version_problem`.
- **FR-018**: A `version_link` naming another repository or branch MUST give `version_problem`.
- **FR-010**: `version_problem` MUST be plain text, in both the history answer and the versions answer. A problem MUST NOT stop the history or refuse the config file. On older commits the same causes give an empty `version` and no problem.
- **FR-011**: The history answer MUST carry `version_file`, or nothing without one.
- **FR-012**: The route for one version MUST open the new points, and their graph MUST be the one in that commit.
- **FR-013**: The webhook MUST report a change to the version file as well as to the graph file.
- **FR-014**: Tags MUST be placed on all the points, by today's rule.
- **FR-015**: The cache of graph bytes, facts and detail MUST be kept per graph file. A version read MUST be kept per version file and key. Old cache files MUST NOT be served.
- **FR-016**: `graph_file_before` and `version_file_before` MUST be optional lists of old paths, and each commit MUST be read from whichever path exists there.
- **FR-017**: The tests MUST use the sample files of `version-gate`'s specification, copied from a named release.

### Key Entities

- **History**: one graph file on one branch, and now optionally one version file, one key and their old paths.
- **Point**: a commit of a history, with `graph_changed`, `version` and `version_changed` beside today's fields.
- **Version problem**: a plain text saying why a history's version cannot be read at the head of its branch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a history of six commits covering all the cases of User Story 1, every point has exactly the expected three values.
- **SC-002**: Each cause of `version_problem` in User Story 3 gives a plain message, and the graph opens in every one of them.
- **SC-003**: Two graphs at one commit return the right bytes in both orders, cold and warm.
- **SC-004**: A history with no version file returns the same points as before this feature.
- **SC-005**: A version file broken in the middle of a history changes only the points the edge cases name.
- **SC-006**: A history over a moved folder returns its points from both sides of the move.

## Assumptions

- The two choices in #344 stand: old paths are declared, and a commit becomes a point only if the graph or the number changed. The rule in #316 that every pull request is a point is not followed.
- Only TOML and JSON are read. Another format gets `version_problem`, and a project uses tags or a component's own `version.toml`; a copy of a package's number is not an answer.
- Passing the new fields through Maxitor's server and drawing them belong to #345.
- Host requests are not bounded here. More points mean more requests for pull requests, so the plan must look at this.
