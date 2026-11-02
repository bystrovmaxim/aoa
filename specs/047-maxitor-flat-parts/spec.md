# Feature Specification: Maxitor parts one level shallower, and `front` named `web`

**Feature Branch**: `feature/issue-305-maxitor-one-level-less-drop-src`

**Created**: 2026-11-01

**Status**: Draft

**Input**: Issue [#305](https://github.com/bystrovmaxim/aoa/issues/305): drop the `src/` level from all five parts of the `maxitor` package, then rename the part `front` to `web` in its folder, its import path and its extra.

A note on vocabulary: this work changes names and folders, so the names and folders are the requirements. They appear here as what must be true, not as a way of building it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contributor reads a shorter tree (Priority: P1)

A contributor opens `packages/maxitor/` and reaches a part's code one folder sooner, in every part alike. Nothing they run behaves differently: every test, check and command gives the result it gave before.

**Why this priority**: This is the reason for the issue. It also carries the most risk, because every build and check reads these folders.

**Independent Test**: After the moves, list the folders under `packages/maxitor/` and run the check run. No `src/` remains except the client's, and every result matches the state before.

**Acceptance Scenarios**:

1. **Given** the five parts `front`, `tools/graph_builder`, `tools/repo_graph_port`, `core/graph_compare` and `core/graph_map`, **When** the moves are done, **Then** each part holds its code directly at `<part>/maxitor/<name>/`, with no `src/` level.
2. **Given** the moved parts, **When** the check run and every test run, **Then** they pass as they did before.
3. **Given** the moved parts, **When** the graphs are rebuilt, **Then** `front/graph.json` and `tools/repo_graph_port/graph.json` are byte for byte the same as before the moves.
4. **Given** a clean environment, **When** the built package is installed with each extra, **Then** `maxitor`, `graph-builder` and `repo-graph-port` start as before.

---

### User Story 2 - A published package still carries its web client (Priority: P1)

The maintainer publishes the package, and the installed server serves the web client, as it does today.

**Why this priority**: The release workflow names the client's output folder by a relative path. A missed line builds the client into the old folder, and nothing fails until someone installs the published package.

**Independent Test**: Build the package the way the release workflow builds it, install it in a clean environment and confirm that the client's files are inside it.

**Acceptance Scenarios**:

1. **Given** the release workflow's build steps, **When** they run after the move, **Then** the built package contains the client's static files.
2. **Given** the container image of the web part, **When** it is built after the move, **Then** the client's files land where the server looks for them.

---

### User Story 3 - The part is called what it is (Priority: P2)

A reader sees `web` instead of `front`. The part holds Maxitor's server and its built web client, so the name now says what is inside. Folder, import path and extra all use the same word.

**Why this priority**: It is a naming correction with a real cost in the graph, so it follows the neutral moves and stays separable from them.

**Independent Test**: Search the tracked files for the old names and run the check run. The old names appear only in old specs and past changelog entries.

**Acceptance Scenarios**:

1. **Given** the renamed part, **When** code imports it, **Then** the path is `maxitor.web`, and `maxitor.front` no longer exists.
2. **Given** a user installing the package, **When** they ask for the part, **Then** the extra is `maxitor[web]`, and `maxitor[front]` no longer exists.
3. **Given** the command `maxitor`, **When** it is run after the rename, **Then** it starts the same server as before.
4. **Given** the distribution, **When** it is built, **Then** its name is still `maxitor`.
5. **Given** the old `front/graph.json`, **When** it is compared with the new `web/graph.json`, **Then** the only difference is `maxitor.front` becoming `maxitor.web`.
6. **Given** the stand's configuration and the CI workflows, **When** they run after the rename, **Then** they use the new names and work as before.

---

### User Story 4 - A reader learns what changed (Priority: P3)

Someone who installs the package reads one changelog article and learns the one thing they have to do: ask for `maxitor[web]` instead of `maxitor[front]`. Every README tree and every path in the documentation shows the new layout.

**Why this priority**: It closes the work, and it comes after the code is settled.

**Independent Test**: Read the changelog article and the READMEs. Follow each path they name and confirm that it exists.

**Acceptance Scenarios**:

1. **Given** the finished work, **When** a reader opens the changelog, **Then** they find one article in plain words about the new extra.
2. **Given** the documentation, **When** a reader follows any path it names, **Then** the path exists.

---

### Edge Cases

- **Other checkouts**: after the merge, an environment installed before it still points at the old folders. Each checkout needs `uv sync`, and the issue says so.
- **Leftover build output**: the ignored built client stays in the old folder of an existing checkout, so an empty-looking `front/src/` can remain on disk. It is not tracked and does not affect the result.
- **Schema address**: the `$id` of `graph_builder/config_schema.json` is the raw address of that file on `main`, and that address contains `src/`. The `$id` follows the file, and the old address stops working. Nothing in this repository fetches it, because the code reads the schema from the installed package.
- **Graph history**: the rename reads as one part removed and one created, once, on the commit of phase 3. This is expected. Comparing graphs across that commit shows this large difference.
- **Client's own `src/`**: `web/client/src/` is the client's source folder and stays.
- **The word "front" in other meanings**: only the part's names change. Ordinary use of the word, such as "front end" in prose, is not touched unless it names this part.

## Requirements *(mandatory)*

### Functional Requirements

**Moving the code**

- **FR-001**: Each of the five parts MUST hold its code at `<part>/maxitor/<name>/`, with no `src/` level.
- **FR-002**: `maxitor` MUST remain a namespace shared by all five parts.
- **FR-003**: What is not code MUST stay in the part's outer folder and out of the built package: tests, `graph.json`, test configuration, container files, READMEs, the client's sources and the CI action.
- **FR-004**: Everything that names a moved path MUST follow it: packaging, test, type-check, lint and dead-code configuration, boundary checks, the check run, container files, ignore rules, the release workflow, tests, examples and documentation.
- **FR-005**: The first line of every moved module MUST name its new path, as Principle III requires.
- **FR-006**: The `$id` of `config_schema.json` MUST name the file's new address.

**Renaming**

- **FR-007**: The part MUST be renamed from `front` to `web` in its folder, its import path and its extra, in one step.
- **FR-008**: The command `maxitor`, the distribution name `maxitor` and the other parts' names MUST NOT change.
- **FR-009**: `web/graph.json` MUST be regenerated, and it MUST differ from the old file only by the renamed module path.

**Delivery**

- **FR-010**: The work MUST land as four commits, one per phase of the issue: (1) `front` moved, (2) the other four parts moved, (3) `front` renamed to `web`, (4) closing.
- **FR-011**: The check run MUST pass after each of the first three phases.
- **FR-012**: The closing phase MUST carry the three tail steps of Principle VI in order: the check run taken to zero, the documentation, one changelog article.
- **FR-013**: Old specs and past changelog entries MUST keep their words.

### Key Entities

- **Part**: a piece of the `maxitor` package with its own folder, its code and its tests. There are five.
- **Graph file**: the saved graph of a part. Its ids are module names, so moving a folder leaves it unchanged and renaming a module path changes it.
- **Extra**: the name a user asks for at install time to get a part and its dependencies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 tracked files outside old specs and past changelog entries name `front/src/`, `graph_builder/src/`, `repo_graph_port/src/`, `graph_compare/src/`, `graph_map/src/`, `src/maxitor`, `maxitor.front`, `maxitor[front]` or `packages/maxitor/front`.
- **SC-002**: 0 `src/` folders remain under `packages/maxitor/`, except `web/client/src/`.
- **SC-003**: Each of the 5 parts is exactly one folder level shallower than before.
- **SC-004**: After phase 2, both graph files are byte for byte the same as before the work. After phase 3, `tools/repo_graph_port/graph.json` is still the same, and replacing `maxitor.web` with `maxitor.front` in `web/graph.json` gives the old file byte for byte.
- **SC-005**: A clean install of the built package with each extra behaves as before, and the package built as for release contains every client file.
- **SC-006**: A user needs exactly 1 change to their install: the extra's name.

## Assumptions

- #288 is closed, so the part `tools/repo_graph_port/` it added is in place and nothing blocks the start.
- The distribution `maxitor` has never been published to PyPI (checked: 404), so nothing outside this repository depends on the old names, and no transition period or alias for `maxitor.front` or `maxitor[front]` is needed.
- Every part is installed in editable mode and every test run uses that install. Without `src/`, each part's `tests/` folder becomes importable by the name `tests`. Nothing imports it by that name today, so this cost is accepted ([research.md](research.md), R2).
- The `aoa-*` packages keep their `src/` level. This work covers `packages/maxitor/` only.
- Principle III opens with "every Python module under `packages/*/src`". Maxitor's modules leave that pattern and keep following the principle. The constitution's wording is the maintainer's, so this work does not edit it.
- The issue's title stays as it is, even though the work now also renames a part.
