# Feature Specification: One Graph per Source, Named by Every Request

**Feature Branch**: `feature/issue-214-graph-per-source`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/214 — Maxitor keeps one graph per process; keep one graph per source and let every request name it. Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-26

- **One graph per process.** The application keeps two shared slots, the loaded graph and the sidebar built from it (`app.py:67-68`). `POST /api/load` downloads a service's `graph-json` and overwrites both (`routes/load.py:42-43`).
- **Reads do not say which graph they want.** Six diagram reads (`/api/v1/list-domains`, `list-entities`, `list-node-types`, `full-graph`, `lifecycle-finite-automaton`, `domain-use-case-diagram`) resolve whatever the slot holds at that moment (`duckdb_graph_holder.py:96`), and `GET /api/sidebar` reads the other slot (`routes/sidebar.py:63`). With nothing loaded, a diagram read is refused with `Graph is not loaded: call POST /api/load first.` and the sidebar answers an empty payload.
- **Users overwrite each other.** If A opens service X and B then opens service Y, A's next read silently returns Y's graph. The public stand serves several users from one process, so this is a live defect.
- **Every open pays the full load.** Because there is only one slot, nothing can be reused: each open re-downloads and rebuilds, about 1.6 s on the server (measured in #245).
- **The first picture can come from the previous graph.** On a deep link the client starts the load and the diagram request at the same time (`client/src/app/App.tsx:48`), so the diagram can be drawn from whatever was in the slot before.
- **The holder resolves on every call.** An action that queries the graph several times resolves it each time, so a reload in the middle of a call can mix two graphs (inferred from the code, not reproduced).
- **Removal is implicit.** Nothing ever removes a graph on purpose: it is replaced by the next load or freed when the process stops.
- **Sources are public.** Maxitor sends no credentials when it downloads `graph-json`, and it has no authentication of its own (`NoAuthCoordinator`, `app.py:62`).

## Clarifications

### Session 2026-10-26 — decisions carried from issue #214

- **The graph is keyed by its source, not by a session.** A graph depends on the service it was read from, not on who reads it; two users of the same source share one built graph. No session identity is introduced.
- **A read that finds no graph builds it.** "Not loaded" stops being an answer to a read that names its source.
- **Leaving a source removes nothing on the server.** A graph is shared, so one user's exit must not affect another's; idle removal cleans up.
- **The deep-link URL format does not change.** `?source=…&view=…` keeps working exactly as today, including on a process that has never seen that source.
- **Two ways to get a fresh graph:** a new "Reload from service" button, and leaving the source and entering it again. Opening a deep link never forces a rebuild.

### Session 2026-10-26 — clarify

- Q: When a graph's freshness window has run out and a read arrives, does the read wait for the source to be checked, and what does it get if the source is unreachable? → A: It gets the old graph at once and the check runs in the background; an unreachable source leaves the old graph in place. (Superseded by the next answer: with no freshness window there is no background check.)
- Q: What default freshness window (TTL) should a built graph have? → A: None. A built graph is never re-checked on a timer; it changes only by an explicit reload (the "Reload from service" button, or entering the source again) or by being removed and rebuilt on the next read.
- Q: How many graphs may one process hold at once by default, given that the stand will be linked from a Habr article? → A: 50, configurable, plus a load criterion: the article's readers almost all open one deep link, so the stand must take a few hundred simultaneous opens of one source. The estimate behind it (not checked against data): thousands of article views in the peak hour, a third of them following the link for a couple of minutes, which gives tens to 200–300 people at once; SC-008 uses 300.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Two users, two graphs, no interference (Priority: P1)

A and B use the same Maxitor at the same time. A opens service X, B opens service Y. Whatever each of them clicks afterwards, in any order, A sees only X's diagrams and B sees only Y's.

**Why this priority**: It is a correctness defect on the public stand: a user is shown another user's graph with no sign that anything is wrong.

**Independent Test**: Two clients against one process, each with its own source, interleaving opens, diagram reads and reloads; every answer belongs to the client's own source.

**Acceptance Scenarios**:

1. **Given** A has X open, **When** B opens Y, **Then** A's next diagram read still returns X's graph.
2. **Given** A and B both have X open, **When** B reloads X from the service, **Then** A keeps getting X (the refreshed one), and no other source is touched.
3. **Given** a read whose action queries the graph several times, **When** a reload of the same source happens during that read, **Then** all the read's queries are answered from one and the same graph.

---

### User Story 2 - Deep links always open the graph they name (Priority: P1)

A user opens a saved or shared link `…/?source=<graph-json url>&view=full-graph`. The page shows that graph, whether the process has never seen the source, has it already, or removed it a while ago.

**Why this priority**: Deep links are how Maxitor is shared; the maintainer named them as something that must not break.

**Independent Test**: Open a deep link against an empty process, against a process that already holds the source, and after the source was removed; each time the drawn graph is the one named in the link.

**Acceptance Scenarios**:

1. **Given** a process that has never seen source X, **When** a deep link to X is opened, **Then** X's graph is shown with no extra step, and the open does not send an explicit reload.
2. **Given** a process whose last loaded graph is Y, **When** a deep link to X is opened, **Then** the first picture drawn is X's, never Y's.
3. **Given** a deep link to an unreachable source, **When** it is opened, **Then** the page falls back to the manual "AOA Service URL" prompt, as today.
4. **Given** a deep link opened while the server is busy (503), **When** the page receives it, **Then** the source stays, the page says Maxitor is busy and asks again, and the prompt does not appear.

---

### User Story 3 - A repeat open costs nothing (Priority: P2)

A user opens a source that is already built. The server answers from the built graph without downloading or rebuilding anything. This is also what lets the stand survive a burst of readers following one link from an article.

**Why this priority**: It removes the load cost from every repeat open and is the cache the rendering work in #245 depends on.

**Independent Test**: Open source X twice; the second open causes no download of X and no rebuild. Then open one deep link 300 times at once on a fresh process; X is downloaded and built once and every open succeeds.

**Acceptance Scenarios**:

1. **Given** X is built, **When** any read for X arrives, **Then** it is answered without downloading X, however long ago X was built.
2. **Given** several reads for a source that is not built yet arrive together, **When** they are answered, **Then** the source is downloaded and built once.
3. **Given** a fresh process, **When** 300 readers open the same deep link at the same moment, **Then** all 300 get the graph and none gets an error.

---

### User Story 4 - Getting a fresh graph on purpose (Priority: P2)

The service behind a source has changed and the user wants to see the new version now.

**Why this priority**: A built graph is never re-checked on a timer, so these are the only ways a changed service reaches the screen while its graph is in use. Leaving and re-entering the address is the maintainer's way today; it must keep working, and a direct button is clearer.

**Independent Test**: With X open, click "Reload from service"; exactly one explicit reload of X is sent, then the sidebar and the current diagram are fetched again, and the URL and selected diagram stay.

**Acceptance Scenarios**:

1. **Given** X is open on a diagram, **When** the user clicks "Reload from service", **Then** X is rebuilt from the service, the same diagram is shown again from the new graph, and the URL does not change.
2. **Given** a reload is running, **When** the user looks at the button, **Then** it is disabled until the reload finishes.
3. **Given** the service is unreachable, **When** the user clicks "Reload from service", **Then** the failure is reported and the diagram already on screen stays.
4. **Given** the user leaves X and types X into the "AOA Service URL" field again, **When** the field is submitted, **Then** X is rebuilt, as today.
5. **Given** no source is open, **When** the user looks at the sidebar, **Then** the button is not shown.

---

### User Story 5 - Unused graphs do not stay in memory (Priority: P3)

Graphs that nobody reads go away on their own, and the process never holds more than a fixed number of them. A user who comes back later does not notice, apart from one slower open.

**Why this priority**: It bounds the memory of a shared process; it matters once the store holds more than one graph.

**Independent Test**: Read source X, wait past the idle timeout without reading it, and confirm X is no longer held; then read it again and get X's graph with no error. Separately, fill the store to its maximum and confirm the least recently read graph is the one removed.

**Acceptance Scenarios**:

1. **Given** X has not been read for the idle timeout (5 minutes by default), **When** the store is next checked, **Then** X is removed.
2. **Given** a browser tab with X open for longer than the idle timeout, **When** the user refreshes it or clicks a diagram, **Then** X's graph is shown again with no error and no prompt; only that first answer is slower.
3. **Given** the store holds its maximum number of graphs, **When** a new source is built, **Then** the graph read least recently is removed.
4. **Given** a read is in progress on X, **When** X is removed or replaced, **Then** that read finishes on the graph it started with.
5. **Given** a user leaves X, **When** they do so, **Then** nothing is removed on the server.

### Edge Cases

- **A read without a source.** Diagram reads that name no source are refused with an error that names the missing parameter. The client never sends such a read; the start page with no source open shows the "AOA Service URL" prompt and asks the server for nothing graph-related.
- **The same source written differently** (trailing slash, different letter case in the host). Each distinct string is its own key; no normalization is promised in this feature.
- **A source that fails to build** (unreachable, not a graph, invalid JSON). The read is refused with the reason, nothing is stored for that source, and any read within the next 10 seconds gets the same refusal without a new download; the first read after that window tries the source again.
- **A failing reload of a source that is already built.** The built graph stays and keeps answering; the failure is reported to whoever asked for the reload.
- **A service that changed while its graph is held.** The held graph keeps answering until an explicit reload, or until it is removed and rebuilt on the next read. There is no timer that re-checks the source.
- **A reader who leaves during a cold build.** The build goes on for everyone else waiting for it, and the graph is stored when it finishes.
- **A tab opened before this feature was deployed.** Its old code sends reads without a source and gets the 400 until the page is reloaded; the reload loads the new code and the tab works again.
- **Many different cold sources at once.** At most a fixed number of builds run at the same time (4 by default); the other reads wait for a slot and are then answered, or get a 503 after 30 seconds of waiting. Without this bound, 300 different sources would build 300 graphs at once, about 15 GiB before the store's own limit could act.
- **Unreachable sources holding the slots.** A download that never answers takes up to 15 seconds (the existing timeout), so four of them occupy every build slot for that long. The 10-second memory of a failed source stops the same bad address from taking a slot again at once; the 30-second wait limit turns a full queue into a clear 503 instead of a hang. Many distinct bad addresses can still fill the slots; that is accepted (see Out of Scope, the allowlist).
- **A reload while the same source is building.** The reload waits for that build, then builds again; the reader sees the reload's graph.
- **A deep link while the server is busy.** A read that waited 30 seconds for a build slot is refused with 503. The page keeps the source and the diagram, reports that Maxitor is busy and asks again, rather than sending the user to the "AOA Service URL" prompt for a source that is perfectly good.
- **A cross-origin client.** When the client is served from another origin than the API, a refusal (400, 422, 503) carries the same CORS headers as a successful answer, so the browser shows the refusal and the client can act on it, rather than reporting a network error.
- **Invalid limit settings.** A maximum or idle timeout that is not a positive number stops the application at start, with a message naming the setting.
- **Several replicas of the process.** Each builds its own graphs on demand; a read landing on a replica that has not seen the source is a cold read, never a wrong graph.

## Requirements *(mandatory)*

### Functional Requirements

**Graph store**

- **FR-001**: The system MUST keep built graphs keyed by source, so that any number of sources are held side by side in one process.
- **FR-002**: A built graph MUST be kept together with the sidebar data built from it, so the two always come from the same source and the same build.
- **FR-003**: The system MUST build a source at most once at a time: concurrent requests for a source that is being built wait for that build instead of starting another.
- **FR-004**: The system MUST hold at most a configured number of graphs; when a new one would exceed it, the graph read least recently is removed. The maximum MUST be configurable and default to 50.
- **FR-005**: The system MUST remove a graph that has not been read for the idle timeout; the idle timeout MUST be configurable and default to 5 minutes.
- **FR-006**: Removing or replacing a graph MUST NOT interrupt a read that is using it; that read finishes on the graph it started with.
- **FR-007**: A single read MUST use one graph for all its queries, even if the same source is replaced while the read runs.

**Reads**

- **FR-008**: Every diagram read and the sidebar read MUST name the source they are for.
- **FR-009**: A read for a source that is not held MUST build it and then answer; it MUST NOT answer "not loaded".
- **FR-010**: A read that names no source MUST be refused with an error that names the missing parameter.
- **FR-011**: A read for a source that cannot be built MUST be refused with the reason, and no graph MUST be stored for that source. The failure MUST be remembered for 10 seconds: reads of that source within that time get the same refusal without a new download; an explicit reload ignores it. Only a failure of the source itself is remembered; a build that could not get a slot (503) is not, so the next read of that source tries to build again.
- **FR-025**: At most a configured number of builds MUST run at the same time across all sources (default 4); further builds MUST wait for a free slot. A read that has waited 30 seconds for a slot MUST be refused with **503** and a message saying Maxitor is busy building other graphs, rather than hang. Single flight (FR-003) still applies inside that bound.
- **FR-026**: Refusals of a graph read (400, 422, 503) MUST carry the same CORS headers as successful answers, a CORS preflight request MUST pass through untouched, and a client on another origin MUST be able to read the `Retry-After` header of a 503.
- **FR-027**: A source MUST reach the store as the same key whether it arrives as the `source` of a read or as the `service_url` of an explicit reload, including addresses that contain `&`, `+`, `%2F` or spaces.
- **FR-028**: The health answer MUST report how many graphs are held, how many builds are running and how many are waiting for a slot, so an operator can see the store's load without a debugger.

**Refresh**

- **FR-012**: A built graph MUST be reused without downloading its source for as long as it is held; nothing re-checks a source on a timer.
- **FR-013**: FR-003 MUST hold at the scale of an article's readers: when 300 reads of one unbuilt source arrive at once, all of them MUST be answered, none MUST fail, and a reader who gives up while the build runs MUST NOT cancel it for the others.
- **FR-014**: An explicit reload of a source MUST download and rebuild that source and MUST NOT affect any other source. A source has at most one build in flight of any kind: a reload that finds a build already running for its source waits for it and then starts its own, so the graph stored last is always the reload's, and an older build can never overwrite it.
- **FR-015**: A failing explicit reload MUST leave the previously built graph of that source in place and report the failure.

**Client**

- **FR-016**: Every request the client makes for graph data MUST carry the source currently open. On a deep link the source MUST be known before the page's first request, so no read leaves without it.
- **FR-017**: Opening a deep link MUST only read; it MUST NOT send an explicit reload.
- **FR-018**: Submitting a source in the "AOA Service URL" field MUST send one explicit reload of that source.
- **FR-019**: Leaving a source MUST clear the browser state only and send nothing that removes a graph.
- **FR-020**: The sidebar MUST offer a "Reload from service" control while a source is open; it sends one explicit reload of the current source, then fetches the sidebar and the current diagram again, keeps the URL and the selected diagram, is disabled while its reload runs, and reports a failure without clearing the diagram on screen. A busy answer (503) to the reload is reported the same way and is not retried automatically: the user decides when to try again.
- **FR-021**: The first picture drawn after opening a deep link MUST come from the source named in that link.
- **FR-022**: The deep-link URL format (`?source=…&view=…`) MUST NOT change; links saved before this feature MUST keep working.
- **FR-023**: An unreachable source on a deep link MUST still fall back to the manual "AOA Service URL" prompt.
- **FR-029**: A busy answer (503) MUST be told apart from a failure of the source: the page MUST keep the source and the diagram on screen, say that Maxitor is busy, and retry the read, and it MUST NOT fall back to the "AOA Service URL" prompt, which would throw away a source that is merely busy. Retries MUST NOT add to the queue they wait for: a 503 carries `Retry-After: 5`; the page waits at least that long before its next try and doubles the pause after each further 503 (5, 10, 20 s), never waiting more than 30 s between tries. One page MUST keep one retry loop, however many reads it holds.

**Tail**

- **FR-024**: The work MUST end with the three steps of Principle VI, in order: the check run taken to zero, the documentation (request contract, the maximum-graphs and idle-timeout settings, what an explicit reload means, the "Reload from service" control, each case as a script and a notebook), and one changelog article.

### Key Entities

- **Source**: the address of a service's `graph-json`, exactly as the user gave it. It is the key of everything below.
- **Built graph**: what Maxitor makes from one download of a source — the queryable graph plus the sidebar data.
- **Graph store**: the process-wide set of built graphs, keyed by source, bounded by a maximum count (50 by default), with for each entry the time it was last read (for the idle timeout and for least-recently-read removal).
- **Explicit reload**: a user's request to download and rebuild one source now.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test with two clients on two different sources, interleaving at least 50 reads and reloads in random order, 100 % of answers belong to the asking client's source.
- **SC-002**: A repeat open of a source that is built causes 0 downloads of that source and 0 rebuilds, and its answer does not wait for any build.
- **SC-003**: 10 concurrent first reads of one unbuilt source cause exactly 1 download and 1 build.
- **SC-004**: Opening a deep link draws the named source's graph first in 100 % of runs, including on a fresh process and after the source was removed.
- **SC-005**: The store never holds more graphs than its configured maximum, and a graph unread for the idle timeout is gone within one further check.
- **SC-006**: A tab left open past the idle timeout, then refreshed or clicked, shows its graph with 0 errors and 0 prompts.
- **SC-007**: A fresh graph can be obtained in both ways — the "Reload from service" control and leaving and re-entering the source — and opening a deep link sends 0 explicit reloads.
- **SC-008**: 300 simultaneous opens of one deep link on a fresh process — the burst a Habr article can bring — are all answered with the graph, with 0 errors, 1 download and 1 build of the source.
- **SC-009**: 20 different cold sources read at the same moment never have more than 4 builds running at once, and all 20 are answered.
- **SC-010**: A reload issued while a cold build of the same source runs ends with the reload's graph stored, never the earlier build's.

## Assumptions

- Every source is a public address: Maxitor sends no credentials, so sharing one built graph between users leaks nothing. If credentials are ever sent, the key must also include the caller (out of scope).
- How the source travels with a read (query parameter or header) is a planning decision; the requirement is only that each read names it.
- Graph identity is the source string as given; no URL normalization is done.
- The stand will be linked from a Habr article. Its readers almost all open one deep link, so the burst is many reads of one source, not many sources; 300 simultaneous opens is an estimate, not a measured figure.
- One process holds the store in memory; several replicas do not share it.
- Fetch timeout and error messages of the download stay as they are today.

## Out of Scope

- Authentication and authorization: who may see which graph.
- Restricting which source URLs Maxitor may download (an allowlist). Without it, anyone can name 50 different sources, push everyone else's graphs out of the store and make the process hold about 2.4 GiB. Each pushed-out reader only waits for one rebuild, so this costs time and memory but never shows a wrong graph; today one user can already replace the single graph for everyone. Protecting recently read graphs from eviction was rejected: when all of them are recent, a new source would have to be refused. The allowlist is the fix and is a separate subject.
- A store shared between replicas.
- Rendering speed of the full graph (#245).
