# Feature Specification: Maxitor's parts in folders named the way people call them

**Feature Branch**: `feature/issue-395-folder-names`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #395, "Maxitor: name the folders of its parts the way people call them (maxitor-web, repo-graph-port, graph-builder)".

## Overview

Maxitor names a history after the folder that holds its graph file (spec 056). Three folders of Maxitor were named for code rather than for people: `packages/maxitor/web` reads `web`, and the two tools use underscores — `repo_graph_port`, `graph_builder` — while every package of the repository and every other mention of the tools (the stand's `repo-graph-port.aoa.run`, the `graph-builder` command) uses hyphens.

The folders move to `packages/maxitor/maxitor-web`, `packages/maxitor/tools/repo-graph-port` and `packages/maxitor/tools/graph-builder`. A folder that holds a graph file carries its history: the graph port follows the file through the move, so the history after it still shows every version before it.

## Clarifications

### Session 2026-11-04

- Q: When a graph file moves with its folder, what becomes of the history before the move? → A: The port follows the file through the move by itself, for every history: it asks git which paths the graph file and the version file had before, and reads each older version at its own path. A history from the config may still list its old paths; the port joins both.
- Q: What does a link to the old path open after the move? → A: What that path holds: the versions up to the move. Links are not redirected; the documentation and the stand use the new paths.
- Q: What of `bystrovmaxim/gameoffer`, whose workflow pins the GitHub Action at the old path by commit? → A: It keeps working, since the pin names a commit. After the merge, a pull request in `gameoffer` moves its workflow to the new path at the merge commit, and is merged once its checks pass.
- Q: Which versions rise? → A: Every level that changes: `repo-graph-port` and the `maxitor` package by a minor step, since the port gains rename-following; `maxitor-web` and `graph-builder` by a patch, since for them only paths change.
- Q: What of the stand? → A: It is rebuilt from the new paths after both changes are merged, and its three services answer on their domains as before, with the history cache kept.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Names that read as their parts (Priority: P1)

A reader opens the graph of Maxitor's web part or of the history port and sees `maxitor-web` or `repo-graph-port`, the names used everywhere else.

**Why this priority**: It is why the folders move.

**Independent Test**: Open the links to `packages/maxitor/maxitor-web/graph.json` and `packages/maxitor/tools/repo-graph-port/graph.json`; the histories are named `maxitor-web` and `repo-graph-port`.

**Acceptance Scenarios**:

1. **Given** the folders moved, **When** a reader opens `…/blob/main/packages/maxitor/maxitor-web/graph.json`, **Then** the history is named `maxitor-web`.
2. **Given** the folders moved, **When** a reader opens `…/blob/main/packages/maxitor/tools/repo-graph-port/graph.json`, **Then** the history is named `repo-graph-port`.

---

### User Story 2 - A history survives the move (Priority: P1)

A reader opens the history of `maxitor-web` after the move and sees every version it had at `packages/maxitor/web`, followed by the versions after the move.

**Why this priority**: A rename that loses the history would trade a name for the past.

**Independent Test**: In a repository whose graph file moved in one commit, the history at the new path lists the versions before the move, each read at the path it had then.

**Acceptance Scenarios**:

1. **Given** a graph file committed three times at `a/graph.json` and then moved to `b/graph.json`, **When** the history of `b/graph.json` is listed, **Then** it holds the three versions and the move, oldest first.
2. **Given** that history, **When** a version before the move is read, **Then** its graph is the file at `a/graph.json` in that commit.
3. **Given** a version file moved with the graph file, **When** the versions are listed, **Then** each carries the version its file held then.
4. **Given** a history from the config that lists `graph_file_before`, **When** git also finds an older path, **Then** both are used, and no path twice.

---

### User Story 3 - Everything that names the folders follows (Priority: P2)

A developer builds, tests, packages and deploys Maxitor exactly as before, with the new paths.

**Why this priority**: A move that breaks the build or the stand is no improvement.

**Independent Test**: The closing check run, the package build and a stand deploy pass with the new paths; a search for the old paths finds them only in history (`CHANGELOG.md`, `specs/`).

**Acceptance Scenarios**:

1. **Given** the move, **When** the closing check run runs, **Then** it passes.
2. **Given** the move, **When** the `maxitor` package is built, **Then** it holds the same modules as before.
3. **Given** the move, **When** the repository is searched for `packages/maxitor/web/`, `tools/repo_graph_port` or `tools/graph_builder`, **Then** only `CHANGELOG.md` files and `specs/` hold them.
4. **Given** the merge, **When** the stand is deployed, **Then** `maxitor.aoa.run`, `demo.aoa.run` and `repo-graph-port.aoa.run` answer as before.

### Edge Cases

- A move git cannot see as a rename (the file rewritten beyond recognition in the same commit): the history starts at the move, as today; a config may list the old path.
- A graph file that moved twice: every earlier path is found, newest first.
- A path that held another graph file before: only the chain of renames of this file counts, not unrelated files that once had that name.
- Import names (`maxitor.web`, `maxitor.repo_graph_port`, `maxitor.graph_builder`), command names, extras and the published package do not change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The folders MUST move: `packages/maxitor/web` → `packages/maxitor/maxitor-web`, `packages/maxitor/tools/repo_graph_port` → `packages/maxitor/tools/repo-graph-port`, `packages/maxitor/tools/graph_builder` → `packages/maxitor/tools/graph-builder`.
- **FR-002**: Every reference to the old paths MUST follow, except in `CHANGELOG.md` files and `specs/`.
- **FR-003**: The graph port MUST find, for every history, the earlier paths of its graph file and of its version file through git's rename detection on its branch, newest first, and MUST read each version at the path it had in that commit.
- **FR-004**: Paths a history's config lists MUST be joined with the ones found, without repeats.
- **FR-005**: The GitHub Action MUST be at `packages/maxitor/tools/graph-builder`; the changelog MUST tell users of the old path to change it when they next update.
- **FR-006**: Import names, commands, extras and the published package's modules MUST NOT change.
- **FR-007**: The versions of `repo-graph-port` and `maxitor` MUST rise by a minor step, of `maxitor-web` and `graph-builder` by a patch.
- **FR-008**: After the merge, `bystrovmaxim/gameoffer`'s workflow MUST use the new action path.

### Key Entities

- **A history's earlier paths**: the paths its graph file and version file had before, newest first, found by git or listed in the config.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The history of `packages/maxitor/maxitor-web/graph.json` lists at least as many versions as the history of `packages/maxitor/web/graph.json` listed before the move, plus the move.
- **SC-002**: The histories of the three graph files of this repository are named `aoa-demo`, `maxitor-web` and `repo-graph-port`.
- **SC-003**: The closing check run, the package build and the stand's deploy pass.

## Assumptions

- A move done with `git mv` and merged as a pull request is a rename git detects on the branch's first-parent line, as long as the file keeps most of its content.
- Untracked files in the moved folders (the client's `node_modules`, built `static/`) move with the folders, since `git mv` renames the folders themselves.
