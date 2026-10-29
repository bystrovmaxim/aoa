# Feature Specification: Maxitor Reads a Graph's History from Its Repository

**Feature Branch**: `feature/issue-288-repo-graph-port`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/288 — Graph history 3/9: maxitor.repo_graph_port reads a graph's history from its repository. Use the issue body as the source of truth; its decisions are settled."

## Context: what is true today, checked on 2026-10-29

- **A service's graph is kept in git.** Every service keeps its current graph in one file, `graph.json`, committed with the code and checked in CI by `graph-builder` (#301, #286). Each merge into the main branch that changed the file is a version; nothing reads those versions yet.
- **Maxitor is one package**, `maxitor` 3.0.0, laid out by kind: its web part in `packages/maxitor/app/` (module `maxitor.viewer`, extra `viewer`, command `maxitor-api`), the `graph-builder` tool in `tools/graph_builder/`, the skills in `skills/`. Maxitor is an internal developer platform; "viewer" undersells its web part.
- **Maxitor's server** runs AOA actions behind its HTTP adapter; the web part's own graph has 214 nodes and 305 edges.
- **The name `maxitor.viewer`** appears across the web part's code and tests, the examples, the docs, the Docker image and the stand, the preview configs, the workflows, the workspace config, the boundary rules, `graph-builder.toml` and the repository's tests.
- **The check run** has 40 steps.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maxitor's web part is called `front` (Priority: P1)

A developer or an operator installs and runs Maxitor's web part by one name that says what it is: `pip install "maxitor[front]"`, then `maxitor`. In the code it is `maxitor.front`; in the repository, `packages/maxitor/front/`. The word "viewer" is gone.

**Why this priority**: The core of this feature plugs into this web part; it must have its right name first, or every later step carries the wrong one.

**Independent Test**: Install the package with the `front` extra in a clean environment and start it with `maxitor`; search the repository for the old name.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** `maxitor[front]` is installed and `maxitor` is run, **Then** Maxitor serves its pages as it did before.
2. **Given** the repository, **When** it is searched outside old specs and past changelog entries, **Then** no file names `viewer` as Maxitor's part.
3. **Given** the web part's graph rebuilt, **When** it is compared with the one before, **Then** they differ only in the prefix of their ids (`maxitor.viewer` → `maxitor.front`).
4. **Given** the package without the `front` extra, **When** `maxitor` is run, **Then** it names the extra to install.

---

### User Story 2 - A history is the merged pull requests that changed the graph (Priority: P1)

Maxitor asks for a service's history and gets its versions, oldest first: one per merged pull request that changed the graph file, each with its pull request's description, the repository's tags that belong to it, and its size. It asks for one version and gets that graph exactly as it was committed.

**Why this priority**: This is what the whole graph history (#273) is built on; without it nothing can be shown or compared.

**Independent Test**: In a small repository with merged branches, direct commits, a merge that does not touch the graph and tags on later commits, ask for the history and for each version.

**Acceptance Scenarios**:

1. **Given** a repository with merged pull requests, **When** the history is asked for, **Then** it lists exactly the commits of the main branch, by first parent, that changed the graph file, oldest first; branch commits and merges that did not touch the file are not listed.
2. **Given** a version made by a pull request, **When** it is listed, **Then** it carries the pull request's number, title, description and link; a version made by a direct commit carries the commit's message.
3. **Given** tags on the repository, **When** the history is asked for, **Then** every tag is placed on exactly one version — a tag on a later commit that did not change the graph on the version before it — and a release's title and link come with its tag.
4. **Given** a version, **When** it is asked for, **Then** its graph file comes back byte for byte as committed.
5. **Given** a graph file that does not pass the protocol's schema of the version it declares, **When** its version is listed, **Then** it is marked refused with the reason.

---

### User Story 3 - A private repository opens by read key, a public one by its link (Priority: P1)

The owner of a private repository gives a colleague a read key; the key opens that one history at the port and nothing else of the repository. A public repository's history opens from a link to its graph file, with no key.

**Why this priority**: Most services' repositories are private; the history must open without opening the repository.

**Independent Test**: Issue a key, open its history; try it on another history of the same repository; revoke it; open a public repository's link without a key.

**Acceptance Scenarios**:

1. **Given** a key issued for one history, **When** it is used, **Then** that history opens, and another history of the same repository does not.
2. **Given** an unknown, revoked or expired key, or a version the history does not have, **When** it is used, **Then** the answer is the same "not found" in each case.
3. **Given** the configuration, **When** it is read, **Then** it holds only each key's hash, name and expiry, never the key.
4. **Given** a public repository's link to its graph file, **When** it is opened, **Then** its history opens with no key and no app installed on it.
5. **Given** Maxitor's log, **When** keys and tokens were used, **Then** none of them appears in it.

---

### User Story 4 - The history stays fresh without hammering the host (Priority: P2)

A pull request is merged, a tag is pushed, a pull request's description is edited: the history shows it promptly. Opening the same version again costs nothing; asking again for an unchanged history costs a header.

**Why this priority**: The host limits requests, and a room of people opening one version should not multiply them.

**Independent Test**: Push, tag and edit against a stand-in host; count the host's requests on repeated reads.

**Acceptance Scenarios**:

1. **Given** a push, a new tag or an edited pull request, **When** the host notifies Maxitor, **Then** the next history shows it without waiting for the fallback interval.
2. **Given** no notification arrives, **When** the history is asked for after the fallback interval, **Then** Maxitor fetches first.
3. **Given** a version read once, **When** it is read again, **Then** the host is not asked.
4. **Given** an unchanged history, **When** it is asked for again, **Then** the answer is "not modified".

### User Story 5 - The port runs on the stand with live access to real repositories (Priority: P1)

The maintainer asks the port at `https://repo-graph-port.aoa.run` for the history of each of their chosen repositories — the private ones by their keys, the public ones by their links. They merge a pull request into one of them, and the new version is in its history at once.

**Why this priority**: The issue is done when the port serves real repositories, not only tests.

**Independent Test**: At `https://repo-graph-port.aoa.run`, ask each configured history for its versions and one version; push to one repository and ask again; push a change that touches no graph file and ask again.

**Acceptance Scenarios**:

1. **Given** the port on the stand with the maintainer's repositories configured, **When** each history is asked for, **Then** it answers with its versions — a private one only with its key, a public one by its link.
2. **Given** a merge into one of them, **When** its history is asked for next, **Then** the new version is there, without waiting for the fallback interval; another history of the same repository whose file the merge did not touch has no new version.
3. **Given** the server, **When** its files, logs and the mirrors' git configs are searched, **Then** the App's token and private key are in none of them; the private key and webhook secret come only from the environment of the port's container, and Maxitor's container has neither.

### Edge Cases

- **A history whose graph file was moved or renamed** — the history follows the configured path only; earlier commits under another path are not versions.
- **A merge that brought several graph changes** — one version: the merge.
- **The same tag on two commits** — impossible in git; a moved tag is read where it now points.
- **A graph file of protocol version `1.0`** — a valid version; its edges carry no `id`.
- **The host unreachable** — the mirror answers from what it holds; the fallback fetch is retried later; nothing is invented.
- **A key used on a public history** — the link alone opens it; a key is not needed and not refused.
- **A repository with no graph file at all** — the history is empty, not an error.
- **Two requests fetching one repository at once** — one fetch runs; the other waits for it.

## Requirements *(mandatory)*

### Functional Requirements

**Maxitor's web part is `front`**

- **FR-001**: Maxitor's web part MUST be named `front` everywhere: the folder `packages/maxitor/front/`, the module `maxitor.front`, the extra `front`, the command `maxitor`, the graph file `front/graph.json`.
- **FR-002**: No tracked file outside old specs and past changelog entries MAY name `viewer` as Maxitor's part; the repository's old-name check MUST fail on one.
- **FR-003**: The web part's graph MUST differ from before only in the prefix of its ids.

**The history**

- **FR-004**: The port `maxitor.repo_graph_port` MUST live in `packages/maxitor/tools/repo_graph_port/`, installed with its own extra and run as a service of its own by its own command, `repo-graph-port`; it MUST be the only part of Maxitor that talks to a host.
- **FR-005**: A history MUST be one graph file on one branch of one repository, named in the port's configuration with its host and its read keys.
- **FR-006**: The versions of a history MUST be the commits of its branch, by first parent, that changed its graph file, oldest first.
- **FR-007**: Each version MUST carry its commit, its date, its pull request's number, title, description and link (or its commit's message when it has none), the repository's tags placed on it with their releases' title and link, and its graph's node and edge counts.
- **FR-008**: A tag on a commit that did not change the graph MUST belong to the version before it; tags MUST be read again, since they can come later.
- **FR-009**: A version's graph MUST come back byte for byte as committed; a graph that does not pass the protocol's schema of the version it declares MUST be marked refused with the reason.
- **FR-010**: Three actions, routes of the port's own server, MUST serve it: `describe` (name, repository, branch, path, number of versions, newest), `history` (the versions, with `after` returning only those after a commit, and "not modified" for an unchanged answer) and `version` (one version's graph, never changing).

**Access**

- **FR-011**: A read key MUST open exactly one history; the configuration MUST keep only its hash, name and expiry; issuing, revoking, listing and checking keys MUST be commands, not web endpoints.
- **FR-012**: An unknown, revoked or expired key and a missing version MUST get the same "not found"; wrong keys from one client MUST be limited per minute.
- **FR-013**: A public repository's history MUST open from a link to its graph file given in the request, with no key, no app and no entry in the configuration.
- **FR-014**: No key or token MAY appear in the port's log, its error texts or its telemetry.

**The host and the cache**

- **FR-015**: A private repository MUST be read through an app installed on it with read-only rights to code and pull requests; its token MUST be short-lived and never written to disk or log.
- **FR-016**: Each repository MUST be read through a partial mirror holding its commits and only the files asked for; one repository MUST never be fetched twice at once.
- **FR-017**: What never changes — a version's graph, its counts — MUST be kept forever by commit; tags and pull request descriptions MUST be refreshed.
- **FR-018**: The host's notifications of a push, a tag or an edited pull request MUST be sent to the port and MUST refresh at once the histories they change, verified by the host's signature; without them, a history older than a set interval MUST be fetched before it is answered.
- **FR-018a**: A notification MUST change only the histories it concerns: a push gives a history new versions only when, by git, its graph file changed on its branch between the push's old and new commits; a pull request refreshes a version only when its merge commit is one; a push or pull request that touches no graph file changes no history.

**Boundaries and rules**

- **FR-019**: The port MUST NOT import the web part or a tool, and the web part MUST NOT import the port (it reads the port over HTTP); being a service, the port MUST keep its own graph file, built from its own code.
- **FR-020**: The core MUST be written by the AOA development rules 41–66 the maintainer adopted for Maxitor: actions with frozen inputs and results, logic in aspects, resources with meaningful methods only, environment through declared context, sensitive values never shown.

**The stand**

- **FR-022**: The port MUST run on the stand as its own container beside Maxitor's, at `https://repo-graph-port.aoa.run`; its image MUST carry `git`; the histories config, the mirrors and the version cache MUST live on the server outside the image (the config by `MAXITOR_HISTORIES`, the cache by `MAXITOR_HISTORY_CACHE`, in a volume).
- **FR-023**: The App's private key and webhook secret MUST come only from the environment of the port's container, put there by the maintainer; they MUST NOT be in the repository, an image, a log, or Maxitor's container.
- **FR-024**: The App's token MUST be passed to git per call in a request header, never in a remote URL, so it is never written to a mirror's config.
- **FR-025**: On the stand, every repository the maintainer chose MUST answer `history` and `version` live, and the App's webhook MUST point at the port, `https://repo-graph-port.aoa.run/api/v1/history/events/github`.

**The tail**

- **FR-021**: The change MUST end with the check run, then the documentation (with an executed example and its Russian draft), then the changelog — one article (Principle VI).

### Key Entities

- **History**: one graph file on one branch of one repository, on one host; it has an id, read keys, and versions.
- **Version**: a commit of the branch, by first parent, that changed the graph file; carries its pull request (or message), date, tags, size, and its graph.
- **Read key**: opens one history; known to the configuration only by its hash, name and expiry.
- **Tag**: a repository tag placed on one version; may name a release with a title and a link.
- **Host**: where repositories live; today one, the code host with its app, tokens and notifications.
- **Mirror**: a partial local copy of a repository, the source every answer is read from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test repository with merged pull requests, direct commits, untouched merges and later tags, the history lists exactly the expected versions with 100% of tags placed correctly.
- **SC-002**: Every version's graph comes back identical, byte for byte, to the committed file.
- **SC-003**: A read key opens 1 history and 0 others; every refusal looks the same.
- **SC-004**: A public repository's history opens with no key in 100% of attempts.
- **SC-005**: No key or token is found in the log after a test run that used them.
- **SC-006**: A repeated read of a version makes 0 requests to the host; a repeated history read of an unchanged history is answered "not modified".
- **SC-007**: A push, a tag or an edited pull request appears in the next history within one notification, without waiting for the fallback interval.
- **SC-008**: After the rename, 0 tracked files outside history name `viewer` as Maxitor's part, and Maxitor starts with `maxitor` after installing `maxitor[front]`.
- **SC-009**: The check run passes, every step.
- **SC-010**: At `https://repo-graph-port.aoa.run`, 100% of the configured repositories answer their history; a push shows in the next history within one webhook, and a push that touches no graph file adds 0 versions.
- **SC-011**: The App's token is found in 0 files, logs or mirror configs on the server.

## Assumptions

- The host is GitHub; GitLab and others come later, one resource each.
- A history follows one branch; its graph file's path is fixed in the configuration.
- `#303`'s digest is added to each version when #303 lands; until then a version carries no digest.
- Maxitor's server as a signed client of the port (a key pair, a short JWT per request) is out of scope; today every reader, Maxitor's browser included, presents a history's read key.
- Showing a history (#289) and comparing versions (#290) are out of scope; gameoffer is not touched.
- Tests use a stand-in host; the stand reads the real repositories. The maintainer creates the GitHub App, installs it on their private repositories, and puts its private key and webhook secret on the server; they add the DNS name `repo-graph-port.aoa.run` and its route in the host's front end, and choose which repositories the port serves.
