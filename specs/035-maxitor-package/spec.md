# Feature Specification: The Protocol in a Folder with No Code; Maxitor as One Package with Extras

**Feature Branch**: `feature/issue-286-maxitor-package`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/286 — Graph history 2.2/10: the protocol in a folder with no code; Maxitor as one package with extras. Use the issue body as the source of truth; every decision in it is settled."

## Context: what is true today, checked on 2026-10-29

- **Three things share one package.** `maxitor-gnomon` 0.1.0 (published) holds the protocol (the graph schemas `1.0` and `1.1`, the config schema, the specification), the `gnomon` command (write, check, validate, skill) and the `gnomon-setup` skill. The schemas' `$id` point at `blob/main/packages/maxitor-gnomon/protocol/…`, which never resolved: that path has not reached `main`.
- **The viewer is a package of its own.** `aoa-maxitor` 2.3.0 (import `aoa.maxitor`) holds Maxitor's server and its built front (2.7 MB), with the front's source beside it, its own graph file and the command `maxitor-api`. It needs AOA, the FastAPI adapter, duckdb, httpx, uvicorn and websockets.
- **AOA depends on the tool for one value.** `aoa-action-machine` requires `maxitor-gnomon` only to read the schema of version `1.1` it checks its export against.
- **The old path is everywhere.** 254 tracked files name `packages/aoa-maxitor`; outside the package itself and old specs they are the preview config, the CI and publish workflows, the ignore file, the root README, the stand's compose file, the docs, the tutorial's examples, `gnomon.toml`, the workspace members, the check run's scripts and the lock file.
- **Every package but one lives under the `aoa` namespace**; the package-boundary rules know `maxitor_gnomon` as the single exception.
- **PyPI**: the name `maxitor` is free; `gnomon` is taken.
- **The preview config** carries an uncommitted `maxitor-api` entry that runs without the dev extras, so starting it strips the dev tools from the environment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A project checks its graphs in CI with a light install (Priority: P1)

A project's CI checks that its graph files are current. It installs Maxitor with no extra, or adds one ready step, and runs `gnomon check`. Nothing of AOA, of Maxitor's server or of its front's dependencies is installed.

**Why this priority**: This is what most other projects will ever install of Maxitor; a heavy install would keep them from adopting the check.

**Independent Test**: In a clean environment, install the package with no extra and run the check on this repository's graphs; list what was installed.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the package is installed with no extra, **Then** `gnomon check` runs, and no AOA package and none of the server's dependencies is installed.
2. **Given** a project's CI, **When** the maintainer adds the ready step with one `uses:` line, **Then** the step checks the project's graph files and fails on a stale one.
3. **Given** a command whose part was not installed (Maxitor's server without its extra), **When** it is run, **Then** it names the extra to install instead of failing on an import.

---

### User Story 2 - Any language follows the protocol (Priority: P1)

A developer of a service in another language — Java, Go, 1C — reads the protocol's README and checks their service's graph with any JSON Schema validator, fetching the schema by its own `$id`. Nothing of Python is needed.

**Why this priority**: A protocol tied to one language is not a protocol; the separation is the reason for this feature.

**Independent Test**: Validate this repository's graph files with a plain JSON Schema validator against the schemas fetched by their `$id`.

**Acceptance Scenarios**:

1. **Given** the protocol's folder, **When** its content is listed, **Then** it holds only the schemas, the specification and its changelog — no code in any language and no package definition.
2. **Given** a schema, **When** its `$id` is fetched, **Then** the schema itself comes back (once the folder reaches `main`).
3. **Given** the copies of the schemas inside the Python packages that ship them, **When** they are compared with the folder's files, **Then** they are byte for byte the same.

---

### User Story 3 - Maxitor is one package whose parts are chosen at install (Priority: P1)

A user installs Maxitor once and chooses what they need: only the command, the viewer, or everything. Maxitor's viewer runs as it does today; the user no longer needs to know that the command and the viewer were once two packages.

**Why this priority**: One version, one changelog and one install are what makes Maxitor a platform rather than a set of tools.

**Independent Test**: Install the package with the viewer's extra and run Maxitor's server and its tests; install it with every extra and run every part.

**Acceptance Scenarios**:

1. **Given** the package installed with the viewer's extra, **When** Maxitor's server starts, **Then** it serves the same pages, diagrams and rooms as before the change.
2. **Given** the package installed with every extra, **When** each command runs, **Then** each works.
3. **Given** the viewer's graph built after the change, **When** it is compared with the graph before, **Then** they differ only in the prefix of their ids (`aoa.maxitor` → `maxitor.viewer`).

---

### User Story 4 - The parts stay independent inside the package (Priority: P2)

A developer changes one part of Maxitor and cannot, by accident, make the light command depend on the viewer or on AOA: the check run fails the moment such an import appears.

**Why this priority**: One package is only cheap while its parts stay apart; without the check, User Story 1 breaks silently, at a user's install.

**Independent Test**: Add an import of the viewer to the command's code and run the check run: it fails naming the import; remove it: it passes.

**Acceptance Scenarios**:

1. **Given** the command's code imports anything of AOA or of the viewer, **When** the check run runs, **Then** it fails naming the module and the import.
2. **Given** the viewer imports the command's schemas or differences, **When** the check run runs, **Then** it passes: that direction is allowed.

---

### User Story 5 - A project is connected by following the README or the skill (Priority: P2)

The maintainer follows only `maxitor`'s README — or asks an agent to run the `gnomon-setup` skill, which the package prints — and connects gameoffer's two services: their graphs saved, their CI checking them. Whatever stops them is fixed in the README or the skill.

**Why this priority**: The documentation moves with the code; a README that still names the old packages would stop every new project at its first step.

**Independent Test**: Follow only the README on gameoffer; at the end, both graphs are saved and its CI runs the check.

**Acceptance Scenarios**:

1. **Given** the package installed, **When** the skill is printed, **Then** it names the new package and the new install commands.
2. **Given** gameoffer, **When** the maintainer follows only the README, **Then** both services' graphs are saved and checked in its CI.

---

### Edge Cases

- **A schema copy drifts from the protocol's folder.** Each Python package keeps its copy beside its code; a test in the check run compares every copy with the folder's file byte for byte and fails on any difference, naming both files.
- **The protocol's `$id` changes.** The schemas' content must not change once published; the `$id` changes here once, because the old addresses never resolved. Nothing else in a schema may change.
- **Someone still installs the old packages.** `aoa-maxitor` 2.3.0 and `maxitor-gnomon` 0.1.0 stay on PyPI and keep working; nothing new is published under those names.
- **A command is run without its extra.** It names the extra instead of raising an import error.
- **The viewer's graph changes.** Its ids change in their prefix only; any other difference is a regression.
- **A path to the old folders survives.** Every tracked file outside old specs and past changelog entries is free of `packages/aoa-maxitor` and `packages/maxitor-gnomon` after the change; old specs and the past entries of every changelog keep their names as history.
- **A second service appears in the package later.** Each service's graph is built from its own subpackages and kept in its own file under the package's `graphs/` folder; the package as a whole has no single graph.
- **The preview config.** Starting the viewer's preview server must not strip the dev tools from the environment.

## Requirements *(mandatory)*

### Functional Requirements

**The protocol**

- **FR-001**: The protocol MUST live in a folder of its own, `packages/open-gnomon-protocol`, holding the graph schemas `1.0` and `1.1`, the specification and its changelog, and nothing else: no code, no package definition, nothing published to a package index.
- **FR-002**: Each schema's `$id` MUST be the raw address of its file in that folder on `main`; nothing else in a schema may change.
- **FR-003**: The specification MUST describe the graph document only — the document, its vocabulary, versions and compatibility, identity. What it says today about the graph file, the project config and the repository's conformance MUST move to `maxitor`'s README.
- **FR-004**: `aoa-action-machine` MUST ship its own copy of the schema it produces, byte for byte the protocol folder's file, MUST check its export against that copy itself, and MUST NOT depend on `maxitor` or on any new package.

**One package**

- **FR-005**: `aoa-maxitor` and `maxitor-gnomon` MUST become one package, `maxitor`, in `packages/maxitor`, with the parts `gnomon` (the command), `viewer` (Maxitor's server and built front, formerly `aoa.maxitor`) and `skills`.
- **FR-006**: Installing `maxitor` with no extra MUST give a working `gnomon` command and MUST NOT install AOA or any dependency of the viewer.
- **FR-007**: The extra `viewer` MUST bring everything Maxitor's server needs; the extra `all` MUST bring everything.
- **FR-008**: A command whose extra is not installed MUST say which extra to install.
- **FR-009**: `maxitor` MUST ship copies of the protocol's graph schemas, byte for byte the protocol folder's files; the check run MUST fail when any copy differs from its source.
- **FR-010**: The viewer MUST work as before: the same pages, diagrams, rooms and command `maxitor-api`.
- **FR-011**: Each service in the package MUST have its own graph file under `packages/maxitor/graphs/`, built from its own subpackages only; today that is the viewer's, `graphs/viewer.json`.
- **FR-012**: The front's source MUST move with the viewer, into the package's folder.

**Boundaries**

- **FR-013**: The check run MUST fail when `maxitor.gnomon` imports anything of AOA or of `maxitor.viewer`, naming the module and the import; `maxitor.viewer` MAY import `maxitor.gnomon`.
- **FR-014**: The package-boundary rules MUST know `maxitor` in place of `maxitor_gnomon`.

**Skills and CI**

- **FR-015**: The `gnomon-setup` skill MUST live in the package's `skills` part and `gnomon skill` MUST print it from the installed package; its links and install commands MUST name `maxitor`.
- **FR-016**: The package MUST offer a ready CI step that installs the project's environment and runs `gnomon check`, usable with one `uses:` line; this repository's CI MUST use it.

**Everything that names the old folders**

- **FR-017**: Every tracked file outside old specs and the past entries of every changelog that names `packages/aoa-maxitor`, `packages/maxitor-gnomon`, `aoa.maxitor` or `maxitor_gnomon` MUST follow the change — the workspace, the boundary rules, the check run, the CI and publish workflows, the stand's compose file, the preview config, `gnomon.toml`, the docs and the examples.
- **FR-018**: The preview config's viewer server MUST run with the dev extras, so starting it keeps the dev tools.
- **FR-019**: Nothing new MUST be published under `aoa-maxitor` or `maxitor-gnomon`; publishing `maxitor` and tagging the protocol's release are the maintainer's, after the merge.

**The tail**

- **FR-020**: The change MUST end with the check run taken to zero, then the documentation (the protocol's README, `maxitor`'s README, the root README's package table, the tutorial's step 26, and an executed example — script and notebook — showing every new case: a no-extra install with `gnomon`, `maxitor-api` naming its missing extra, a graph checked against the protocol with a plain JSON Schema validator, the import `maxitor.viewer`), then the changelog — one article (Principle VI).

### Key Entities

- **Protocol folder**: the standard — graph schemas by version, the specification, the changelog. No code. Released by a git tag.
- **Schema copy**: a protocol schema kept inside a Python package beside its code; always byte for byte the folder's file, which the check run proves.
- **`maxitor` package**: one installable unit with parts; its version and changelog cover every part.
- **Part**: a subpackage of `maxitor` — `gnomon`, `viewer`, `skills` — with its own allowed imports.
- **Extra**: a named choice at install time that brings one part's dependencies: none (the command), `viewer`, `all`.
- **Service graph file**: one per service in the package, under `graphs/`, built from that service's subpackages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean install of the package with no extra installs zero AOA packages and zero dependencies of the viewer, and `gnomon check` passes on this repository's graphs.
- **SC-002**: 100% of the schema copies shipped by Python packages are byte for byte the protocol folder's files.
- **SC-003**: The protocol's folder holds zero files of code and zero package definitions.
- **SC-004**: The viewer's graph after the change differs from the graph before in nothing but the prefix of its ids.
- **SC-005**: Every test of the viewer and of the command that passed before the change passes after it.
- **SC-006**: Zero tracked files outside old specs and past changelog entries name the old folders or the old imports.
- **SC-007**: An import of the viewer or of AOA from the command fails the check run in 100% of attempts; removing it makes the check run pass.
- **SC-008**: A project adds the graph check to its CI with exactly one `uses:` step.
- **SC-009**: Following only the README, the maintainer connects gameoffer's two services with no step outside it.
- **SC-010**: The check run passes, every step.

## Assumptions

- The protocol's content (schemas `1.0`, `1.1` and their meaning) does not change; only its home and the schemas' `$id` do.
- The viewer's front stays bundled with its server; splitting them is out of scope.
- `maxitor`'s first version number is chosen in the plan.
- Old specs under `specs/` keep their paths: they are history.
- Reading a graph's history from its repository joins the package in #288 as `maxitor.repo_graph_port`, with an extra of its own; this feature leaves room for it and adds none of it.
- Changes in gameoffer (its config, graph files and CI) are its own; this feature only makes the README and the skill that it follows correct.
- Publishing to PyPI and tagging releases happen after the merge, by the maintainer.
