# Feature Specification: A Service Keeps Its Current Graph in One File, by the Format of maxitor-gnomon

**Feature Branch**: `feature/issue-301-gnomon-graph-file`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/301 — Graph history 2.1/10: a service keeps its current graph in one file, by the format of maxitor-gnomon. Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-28

- **A graph exists only while a service runs.** AOA builds a service's graph from its code (`NodeGraphCoordinator`) and serves it as JSON; nothing keeps it. For #273 (graph history), the history of a graph is the git history of one file: the graph as it is now, committed with the code; every merge into `main` that changes the file is a version. History is taken only from that source — no hand-kept snapshots or indexes.
- **The graph's format belongs to AOA today.** Its JSON Schema is `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.json`, published as `GRAPH_JSON_SCHEMA` and used in 13 places in `aoa-action-machine` and once each in `aoa-demo` and `aoa-maxitor`. Its `schema_version` is `1.1` since #285 (every edge has an `id`); version `1.0` (edges without `id`) is recoverable from git at `f260e2e6`.
- **A graph depends on what its process imported.** The demo's graph is 3213 nodes and 4841 edges; built in a process that has also imported Maxitor, it is 3422 nodes and 5144 edges, because Maxitor's own actions join it. Every graph must therefore be built in a process of its own.
- **The demo's graph as a file** — sorted keys, an indent of two spaces — is 4.47 MB and 90 533 lines; building and exporting it takes about 0.6 s.
- **The demo's builder hides an invalid graph.** When the graph fails its checks, it falls back to a debugging coordinator instead of failing.
- **Maxitor is an AOA application** and serves its own graph — the coordinator its machine was built with.
- **The repository assumes every package lives under the `aoa` namespace.** The package-boundary rules (`scripts/package_boundaries.toml`) and the packaging smoke test both look under `packages/*/src/aoa/…`; a package outside that namespace is new to both. Each package has its own job in `publish.yml`; the check run's steps are a table in `scripts/check_run.py`.
- **A real target project**, gameoffer, has two services that build their graph the same way (import their model, walk their `resources` and `actions` packages, build the coordinator) and serve it at `/graph-json`. Its hand-kept `graph_history` folders will be deleted; its history will start from its first graph file.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A project starts saving its graph by following one instruction (Priority: P1)

The maintainer opens the README of `maxitor-gnomon`, follows its Get started steps on a project that has never saved its graph — gameoffer, after this feature — and ends with each of the project's graphs saved in its repository and checked on every pull request. Nothing beyond the steps is needed.

**Why this priority**: This is what the feature is for: every project that starts saving now has a longer history when the rest of #273 lands.

**Independent Test**: Follow only the Get started steps on a project without graph files; at the end, its graph files are committed and its CI fails when one goes stale.

**Acceptance Scenarios**:

1. **Given** a project without graph files, **When** the maintainer follows only the Get started steps, **Then** each of its graphs is saved to its file and committed, and its CI runs the check.
2. **Given** a step the maintainer cannot follow as written, **When** it is found, **Then** the step is fixed in the README, not worked around.
3. **Given** a developer who forgot to update the graph file, **When** CI fails and they run the writer, **Then** one more commit to the same branch makes CI pass — no new pull request is opened.

---

### User Story 2 - Every merge carries its own graph (Priority: P1)

A developer changes the model and opens a pull request. If the graph file was not updated, CI fails and says what changed in the graph and how to update the file; after updating it, CI passes. A pull request that does not change the model needs nothing.

**Why this priority**: A merge without its graph would be a version missing from the history, and nobody would notice.

**Independent Test**: Change the model without updating the file and run the check: it fails naming the difference. Write the file and run the check: it passes.

**Acceptance Scenarios**:

1. **Given** a graph file that matches the code, **When** the check runs, **Then** it passes.
2. **Given** a change to the model and a file not updated, **When** the check runs, **Then** it fails, naming each difference by the ids the graph carries (for example, an edge whose target changed, with the old and the new target) and saying how to update the file.
3. **Given** a file that holds the right graph in a different layout (another indent, another key order), **When** the check runs, **Then** it fails saying that only the formatting differs.
4. **Given** a graph whose build fails, **When** the check or the write runs, **Then** it fails, showing the build's command and output.

---

### User Story 3 - An unchanged graph makes no new version (Priority: P1)

Writing a graph that did not change leaves its file exactly as it was, so git sees no change and no new version appears in the history.

**Why this priority**: A file that changed on every write — a date, a tool version, a different order — would turn every merge into a "version" and bury the real changes.

**Independent Test**: Write all graphs twice in a row; the second write changes no file.

**Acceptance Scenarios**:

1. **Given** the same code, **When** a graph is written twice, **Then** the two files are the same bytes.
2. **Given** an unchanged graph and its file, **When** the graph is written again, **Then** git reports no change.
3. **Given** any graph file, **When** it is read, **Then** it holds the graph and nothing that changes by itself (no build time, no tool version).

---

### User Story 4 - The graph's format has its own versioned home (Priority: P2)

The graph's schema lives in `maxitor-gnomon`, a package that knows nothing about AOA, so any project whose graph follows the format can keep a history. Every published version of the schema stays as it was; a graph is checked against the version it declares.

**Why this priority**: It is the first step towards an open format; the history of graphs must not depend on reading AOA's code.

**Independent Test**: Check a 1.1 graph and a 1.0 graph against their versions; check a graph that declares an unknown version.

**Acceptance Scenarios**:

1. **Given** a graph declaring `1.1`, **When** it is checked, **Then** it is checked against the 1.1 schema; a 1.1 graph with an edge missing its `id` fails.
2. **Given** a graph declaring `1.0`, **When** it is checked, **Then** it is checked against the 1.0 schema and passes.
3. **Given** a graph declaring a version the package does not know, **When** it is checked, **Then** it is refused, naming the version.
4. **Given** everything in this repository that uses AOA's graph schema today, **When** the schema has moved, **Then** it works unchanged.
5. **Given** the new package, **When** anything in it imports from AOA, **Then** the check run fails.

---

### User Story 5 - The config says how to build and where to save each graph (Priority: P2)

A project writes one config file in its repository root listing each of its graphs: a name, the folder its build runs in, a command that prints the graph, and the file it is saved to. The project, not the tool, decides how its graph is built — from its code, from its running service, or any other way.

**Why this priority**: Projects build their graphs differently; only the project knows how. The config is the single place where it says so.

**Independent Test**: Read a valid config and a config with each kind of mistake.

**Acceptance Scenarios**:

1. **Given** a valid config, **When** it is read, **Then** its graphs come back in the order written.
2. **Given** a config with a missing field, a repeated graph name, or two graphs saved to one file, **When** it is read, **Then** it is refused, naming the graph and the field.

---

### User Story 6 - This repository saves its own graphs (Priority: P2)

The demo and Maxitor each save their graph, and this repository's check run fails when either file is stale — the repository follows the rule it asks of others.

**Why this priority**: It proves the whole path on two real graphs, and gives #273 its first histories.

**Independent Test**: Run the check on the committed files; change the demo's model and run it again.

**Acceptance Scenarios**:

1. **Given** the committed files and an unchanged model, **When** the check run passes, **Then** its last step writes both graphs and changes no file.
2. **Given** a change to the demo's model, **When** the check run passes, **Then** its last step updates the demo's `graph.json`, and the change shows in `git diff` to be committed with the code.
4. **Given** a check run in which any other step failed, **When** it ends, **Then** the graph step did not run, and the log says it was skipped because of the failures.
3. **Given** the two files, **When** they are read, **Then** the demo's holds only the demo's graph and Maxitor's only Maxitor's.

### User Story 7 - An agent sets a project up, and keeps it set up, with one skill (Priority: P1)

`maxitor-gnomon` ships a skill for coding agents, `gnomon-setup`, that knows nothing about any project. Its one command, **Setup**, serves both the first setup and every later one. It searches the repository for every service that produces a graph; for graphs already in `gnomon.toml` it checks that the build still works, that what it prints passes `gnomon validate`, and that the file is current; for new ones it works out a build command and proves it with `gnomon validate`. It then shows the user a table — what it found, what works, what is broken or stale, what is new, with the command and the file for each — asks how to set it up, and only after the answer changes `gnomon.toml`, writes the graph files and adds `gnomon check` to the project's CI. It never commits on its own.

**Why this priority**: It is the second way to start, and the one a platform's project-initiation prompt will build on; the maintainer checks it on gameoffer.

**Independent Test**: In this repository, run Setup with no `gnomon.toml`, then again with it, then with one entry broken.

**Acceptance Scenarios**:

1. **Given** a repository with no `gnomon.toml`, **When** Setup runs, **Then** it lists every service with a graph, the build command it proposes for each, its proof (the schema version and counts from `gnomon validate`) and the file — and asks before writing anything.
1a. **Given** a service with a graph, **When** Setup proposes where to save it, **Then** it offers places that follow the repository's own conventions, the standard `<service folder>/graph.json` when none fits, and accepts a place the user names.
2. **Given** a candidate command that does not print a valid graph, **When** Setup proves it, **Then** it reports the refusal instead of proposing the command.
3. **Given** a set-up repository, **When** Setup runs again, **Then** it reports each configured graph as current, stale or broken, and any service with a graph that is not configured yet, and asks before changing anything.
4. **Given** the user's answer, **When** Setup finishes, **Then** `gnomon.toml`, the graph files and the CI check are in place, and `gnomon check` passes.
5. **Given** a skill file read from a link by an agent that has not installed it, **When** the agent follows it, **Then** it first saves the skill where its own skills live and then runs Setup at once, without waiting for a restart.
6. **Given** gameoffer, **When** the maintainer starts the skill in any of the three ways the README gives, **Then** both services are set up; a second run after a change finds the change; whatever goes wrong is fixed in the skill.

### Edge Cases

- A build prints something that is not JSON, or JSON that does not match the schema of its declared version: nothing is written, and the refusal names the graph.
- A build succeeds but prints a graph without `schema_version`: refused as not declaring a version.
- A graph file is missing: the check fails saying the file does not exist and how to create it.
- A build takes long or never ends: the writer gives up after a time limit and names the graph. [Default: a generous limit stated in the plan.]
- The demo's builder falls back to a debugging coordinator on an invalid graph: what it prints is checked against the schema like any graph; an invalid graph is refused there.
- Two graphs of one config build in the same folder: each still runs in a process of its own.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A new package, `maxitor-gnomon`, MUST hold the graph's schema, the config's format and the writer, and MUST import nothing from AOA; the check run MUST fail if it does.
- **FR-002**: Every published version of the graph schema MUST be kept as its own file that is never changed afterwards; versions `1.0` (recovered from git) and `1.1` (today's, moved unchanged) MUST be present.
- **FR-003**: A graph document MUST be checked against the schema of the version it declares; a missing or unknown version MUST be refused by name.
- **FR-004**: AOA MUST take its graph schema from `maxitor-gnomon`; everything that uses AOA's graph schema today MUST keep working unchanged.
- **FR-005**: The config MUST be one file in a repository's root listing graphs, each with a unique name, a folder the build runs in (default: the root), a command that prints the graph document, and the file it is saved to; a config with a missing field, a repeated name or two graphs saved to one file MUST be refused, naming the graph and the field. The config's format MUST be published by `maxitor-gnomon` with its own schema.
- **FR-006**: A writer MUST read the config and, for each graph, run its build in a process of its own in its folder, check the printed document against its declared schema version, and write it with sorted keys, an indent of two spaces and a final newline. The writer lives in `maxitor-gnomon` (decided by the maintainer on 2026-10-28): it depends on no engine — it runs the command the config names, checks the JSON it prints against the schema and writes the file — so any project can use it, and AOA gains nothing but taking its schema from the package.
- **FR-007**: A graph file MUST hold the graph document and nothing else; writing a graph that did not change MUST leave its file byte for byte as it was.
- **FR-008**: A check mode of the writer MUST write nothing and MUST fail when a file differs from what its build prints, naming each difference by the ids the graph carries, or saying that only the formatting differs, and in both cases how to update the file. The commands are `gnomon write` and `gnomon check` (decided by the maintainer on 2026-10-28); `check` is the check mode.
- **FR-009**: A failing build MUST be reported with its command and its output; a document that is not JSON or does not match its schema MUST NOT be written.
- **FR-010**: This repository MUST keep a config listing the demo's graph and Maxitor's own graph, each built in a process of its own, and MUST commit both graph files. Its check run MUST run `gnomon write` on them as its last step, and only when every other step passed — a run that already failed opens no pull request, so its graphs are not built (decided by the maintainer on 2026-10-28). Like Ruff's auto-fix, the step may change the graph files, and those changes are part of the change; a skipped step says in the log that it was skipped and why. A graph that fails its schema fails the step.
- **FR-011**: The new package MUST be built, tested and published like the other packages: its build and its tests in the check run, its job in `publish.yml`, and the package-boundary rules and the packaging smoke test extended to a package outside the `aoa` namespace.
- **FR-012**: The package's README MUST hold a Get started section of numbered steps that take a project from no graph files to its graphs saved and checked in CI, including a CI step ready to copy; after this feature, the maintainer follows only these steps on gameoffer's two services.
- **FR-012c**: `maxitor-gnomon` MUST ship a skill, `gnomon-setup`, as one self-contained file inside the package, naming nothing about any particular project. Its one command, Setup, MUST serve both the first setup and every later one: find every service that produces a graph; check every configured graph (its build runs, its output passes `gnomon validate`, its file is current); work out and prove a build command for every new one; for each graph, ask where its file goes — offering places that follow what the repository already does (where it keeps generated or exported files, existing graph files, each service's own folder), the standard `<service folder>/graph.json` when nothing fits, or a place the user names; show the user what it found and ask; only then change `gnomon.toml`, write the graph files and add `gnomon check` to the project's CI; never commit. The skill MUST begin with what an agent that read it from a link does first: save it where its own skills live (naming where for the agents it knows), then run Setup at once. Until `maxitor-gnomon` is published, the skill runs `gnomon` from the repository's git (a pinned commit in CI), and says how to switch to the published package.
- **FR-012d**: `gnomon validate <file | ->` MUST check one graph document (from a file or standard input) against the schema of the version it declares and print that version and the number of nodes and edges, or the refusal; it writes nothing.
- **FR-012e**: `gnomon skill` MUST print the skill's file, so it can be saved into an agent's skills folder from the command line.
- **FR-012f**: The README MUST give three ways to start, each ready to copy: (1) by hand — the Get started steps; (2) from the command line — save the skill with `gnomon skill` into the agent's skills folder, then ask the agent to run Setup; (3) with a very short prompt to an agent — one sentence giving the skill's raw link and asking the agent to install and run it.
- **FR-012a**: The README MUST explain, as numbered steps, how a graph travels with a pull request: (1) before pushing, the developer or agent changes the model, runs the writer, and commits the updated graph file with the code on the same branch; (2) the pull request holds both the code and its graph; (3) CI runs the check, which builds the graph from the code and compares it with the file, writing nothing; (4) if the file was not updated, CI fails naming the difference, and the developer runs the writer and pushes one more commit to the same branch — the same pull request, never a new one; (5) the merge brings the code and its graph into `main` together, and that merge is a version of the history.
- **FR-012b**: CI MUST only check graph files and MUST NOT write or commit them; a graph file always reaches `main` inside the pull request that changed the graph.
- **FR-013**: The change MUST end with the check run taken to zero, the documentation and the changelog, in that order (Principle VI). The documentation is: the package's README (with its Russian draft beside it); in AOA's guide, `docs/tutorials/step-00-get-started.md` (a short section on saving the graph from day one, with the three ways to start, and `maxitor-gnomon` in the repository map) and a new section of `docs/tutorials/step-26-maxitor.md` on the graph saved with every change; the packages table of the root `README.md`; a line under Maxitor in `docs/index.md`; and `examples/step_26_maxitor/12_graph_file.py` with its executed notebook, showing every case: the repository's config, a saved graph checked against its schema, a rebuilt graph equal to its file, a stale copy with its differences by id, a copy that differs only in formatting, and an unknown schema version refused. Each changed page gets its Russian draft.

### Key Entities

- **Graph document**: one graph as JSON — `schema_version`, `nodes`, `edges`, every element with an `id`.
- **Schema version**: one published, never-changed JSON Schema for graph documents; `1.0` and `1.1` today.
- **Config**: the repository's list of graphs — name, build folder, build command, file.
- **Graph file**: the saved document of one graph, committed with the code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Following only the Get started steps, the maintainer sets up gameoffer's two services with no step missing; every stop is fixed in the steps.
- **SC-002**: 100 % of writes of an unchanged graph leave its file unchanged; two writes of the same graph give the same bytes.
- **SC-003**: After any change to the demo's model that changes its graph, the check fails and names at least the changed elements by id.
- **SC-004**: The demo's committed graph has 3213 nodes and 4841 edges (as built on its own), and Maxitor's committed graph holds none of the demo's nodes.
- **SC-005**: Every existing test that uses AOA's graph schema passes unchanged after the move.
- **SC-007**: On gameoffer, started in each of the README's three ways, the skill sets up both services, asks before writing, and ends with `gnomon check` passing; a second run after a change finds it; every stop is fixed in the skill or the README.
- **SC-006**: The check run is green with the new package's build, its tests and the graph step in it, and fails when the package imports from AOA; the graph step adds only a few seconds to a green run (measured in the plan) and none to a failing one.

## Assumptions

- The schema itself does not change in this feature: `1.1` moves as it is; separating it from AOA is for later versions, which will be added as new files beside the old ones.
- The config's build command prints the whole graph document to standard output; anything a project needs to build its graph (its environment, its imports) is the command's business.
- The demo's graph file is large (about 4.5 MB); git stores it as deltas between versions, and that is accepted.
- Reading saved graphs and their history (#286), the history index, the comparison of two graphs and the gateway for private repositories (#287, #288) are out of scope.
- Publishing `maxitor-gnomon` to PyPI is a release step outside this feature; until then the skill and CI run it from git.
- A platform-wide project-initiation prompt that installs all of the platform's skills is a later issue; it will install and run this skill.
