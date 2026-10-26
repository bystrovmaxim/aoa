# Feature Specification: A Built Graph Without the Indexes It Does Not Need

**Feature Branch**: `feature/issue-268-graph-memory-indexes`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/268 — Maxitor: a built graph takes 48 MiB, four fifths of it indexes; check whether the diagram queries need them. Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-26

- **One built graph costs tens of MiB, mostly indexes.** Re-measured on the reference source (`https://admingameoffer.aoa.run/graph-json`), which has grown since the issue was written: 326 063 bytes, 440 nodes, 550 edges. One built graph takes **43.5 MiB**, of which **38.0 MiB is indexes** (`ART_INDEX`), 5.3 MiB table data and 0.2 MiB long strings. The issue's own figures (306 754 bytes, 47.9 MiB, 37.8 MiB of indexes) were taken on the earlier version of the same source; the index share is the same.
- **Where the indexes come from.** Every one of the 21 node tables declares its `id` as a primary key (`duckdb_graph_resource.py`, `_install_database`). After the rows are loaded, `_install_post_load_objects` (not `_install_database`, as the issue says) adds 62 indexes on the 31 edge tables (`source_id` and `target_id` of each) and 2 on `state`. That is 85 index structures for about a thousand rows.
- **The queries are fast.** The full-graph query on the reference graph takes about 5 ms (median of 7 runs, one outlier at 10.9 ms), and a whole build takes about 120 ms.
- **A duplicate node `id` is refused today, only by the primary key.** A graph with the same node twice fails to build with `Constraint Error: Duplicate key "id: …" violates primary key constraint.` No test covers this. The primary key is per table: the same `id` in two different node tables is accepted today.
- **The store multiplies the cost.** #214 lets one process hold up to 50 built graphs. The issue measured that on macOS a dropped graph's memory goes back to the process but not to the operating system, so the process keeps its peak size. The stand runs Linux, where this has not been measured.

## Clarifications

### Session 2026-10-26

- Q: The diagram queries take about 5 ms, so 20 % of that (1 ms) is within run-to-run noise. When is a slowdown after removing indexes acceptable? → A: When the median grows by at most 20 % or by at most 1 ms, whichever is larger, and in every case stays at or under 50 ms on the reference source.
- Q: A primary key refuses a duplicate `id` only inside one node table today; the same `id` in two different node tables is accepted. What scope must the check that replaces the primary keys have? → A: The same as today: a duplicate inside one node table is refused, a repeat across tables is accepted.
- Q: How is the result protected from someone bringing the indexes, and the memory, back later? → A: By a test in the suite: one built test graph must stay at or under a set memory ceiling, with a margin, so any heavy structure added back to the build fails it.

### Session 2026-10-26 — review

- The issue's acceptance was all or nothing: a third of the memory, or no change. A safe variant that halves the memory but misses a third would then be thrown away. Decision: ship the smallest variant that keeps the answers and the timings; leave the schema unchanged only if nothing smaller exists (FR-005, FR-009). The issue's §6, criterion 2, was rewritten to match on 2026-10-26.
- The database's own memory figure is not the process's: on 2026-10-26 the process gained 54.3 MiB per graph today and 22.0 MiB without primary keys and indexes, while the database reported 43.5 and 13.4. The process figure is measured before and after (FR-004), and SC-006 is stated in it.
- The guard checks the shape of the schema as well as the memory (FR-013): the database's catalogue lists the 64 indexes and 21 primary keys today, and none in the expected variant, so an index under any name is caught, not only a heavy one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowing what a graph costs and what each index is for (Priority: P1)

The maintainer wants to decide about the indexes from numbers, not guesses. For any graph they can see how much memory a built graph takes and where it goes, how long the build and each diagram query take, and which index each query actually uses.

**Why this priority**: Every other story depends on these numbers. If they show that the hypothesis is wrong, they are the whole result of the work.

**Independent Test**: Run the measurement on the reference source and on the largest graph in the tests. The output lists memory by category, build time, the time of each diagram query and of the sidebar build, and for each index the queries that use it.

**Acceptance Scenarios**:

1. **Given** a graph, **When** the maintainer runs the measurement, **Then** they get its memory by category, its build time and the median time of each of the six diagram queries and of the sidebar build.
2. **Given** the current set of indexes, **When** the maintainer reads the usage table, **Then** every index appears with the list of queries that use it, and an index used by no query is shown as unused.
3. **Given** the measurement is run twice on the same graph, **When** the two results are compared, **Then** memory figures are identical and time figures are close enough to tell a real change from noise.

---

### User Story 2 - Graphs that take a fraction of the memory and answer the same (Priority: P1)

A process that holds many graphs takes several times less memory, and nobody looking at the diagrams can tell that anything changed: every answer is the same and none is noticeably slower.

**Why this priority**: This is the point of the issue. With 50 graphs at 43.5 MiB each, the graphs alone take about 2.1 GiB (the issue's 2.4 GiB was computed at 47.9 MiB).

**Independent Test**: Measure one built graph of the reference source before and after the change, compare every diagram answer byte for byte, and compare the timings from User Story 1.

**Acceptance Scenarios**:

1. **Given** the reference source, **When** it is built after the change, **Then** the graph takes at most a third of the memory measured before the change.
2. **Given** any graph in the tests, **When** each of the six diagram queries and the sidebar build runs before and after the change, **Then** every answer is byte for byte the same.
3. **Given** the measurements, **When** the maintainer compares timings before and after, **Then** no diagram query and no sidebar build becomes noticeably slower (see FR-007).
4. **Given** the smallest variant that keeps the answers and the timing bound is smaller than today but above a third, **When** the work ends, **Then** that variant ships and the pull request says how far it is from a third and why.
5. **Given** no variant that keeps the answers and the timing bound is smaller than today, **When** the work ends, **Then** the schema is unchanged and the pull request carries the measurements that show it.

---

### User Story 3 - A broken graph is still refused (Priority: P2)

A service whose `graph-json` lists the same node twice is a broken service. Opening it in Maxitor fails with a message that says which node is duplicated, just as it does today, whatever happens to the indexes.

**Why this priority**: Today this protection comes only from the primary keys. Removing them without a replacement would silently draw a wrong diagram.

**Independent Test**: Build a graph whose payload contains one node twice; the build is refused and the message names the duplicated `id`.

**Acceptance Scenarios**:

1. **Given** a payload with one node listed twice, **When** it is built, **Then** the build is refused and the message names that node's `id`.
2. **Given** a payload with no duplicates, **When** it is built, **Then** it builds as before.
3. **Given** a payload whose duplicate is refused, **When** it is opened from Maxitor, **Then** the user gets the same kind of refusal as for any other source that cannot be built, and nothing is stored for that source.

---

### User Story 4 - Knowing how the stand's memory behaves (Priority: P3)

The operator of the stand knows what to expect from the process size on Linux: whether memory comes back to the system when graphs are dropped, or whether the process stays at its peak. The answer is written in the documentation of the store's limits.

**Why this priority**: It decides how the store's limit translates into memory on the stand, but it changes no behaviour.

**Independent Test**: Repeat the issue's RSS table (0, 1, 5, 10 graphs held, all dropped, 3 built again) inside the stand's container image, and find the result in the documentation.

**Acceptance Scenarios**:

1. **Given** the stand's container image, **When** graphs are built, held and dropped in the issue's sequence, **Then** the process size at each step is recorded.
2. **Given** memory is not returned to the system there either, **When** the operator reads the store's documentation, **Then** it says that the process size is set by the most graphs held at once, and whether a setting changes that.

### Edge Cases

- **An index no query uses, but one that keeps a query from getting slow on a larger graph.** The decision covers the reference source and the largest graph in the tests, not only the smallest.
- **A query that gets faster without an index.** That is allowed; only slowing down is bounded.
- **The same `id` in two different node tables.** Accepted today (the primary key is per table) and accepted after: the check that replaces the primary keys keeps that scope.
- **A duplicated edge** (the same source, target and type twice). Not refused today, and not refused after.
- **An empty graph.** Builds, as today, and answers every query with an empty result.
- **Timings on a busy machine.** A single slow run must not decide anything; the measurement uses a median of several runs.
- **Linux cannot be measured locally.** If the stand's container image cannot be run, the result says so and records what was measured instead.

## Requirements *(mandatory)*

### Functional Requirements

**Measurement**

- **FR-001**: The repository MUST provide a measurement that, for a given graph, reports the memory of one built graph by category, the build time, and the median time of each of the six diagram queries and of the sidebar build over several runs.
- **FR-002**: The measurement MUST be recorded for the reference source and for the largest graph in the tests, before any index is changed.
- **FR-003**: For every index the build creates, the work MUST establish which of the six diagram queries and the sidebar build use it, and record the result as a table in the issue before the schema is changed.
- **FR-004**: Before and after the change, the process size gained per built graph of the reference source MUST be measured in one process holding 10 such graphs, and reported next to the database's own figure of FR-001. The issue's problem is the process; the database's figure alone does not show it.

**The change**

- **FR-005**: Of the schemas that meet FR-006 and FR-007, the build MUST use the one whose whole build takes the least memory. Schemas are compared as whole builds, never by subtracting the cost of a removed structure: without the 64 indexes but with the primary keys, the reference graph grows from 43.5 to 50.7 MiB.
- **FR-006**: Every answer of the six diagram queries and of the sidebar build MUST be byte for byte the same after the change, on every graph in the tests.
- **FR-007**: After the change, on the reference source and on the largest graph in the tests, the median time of each diagram query and of the sidebar build MUST grow by no more than 20 % or by no more than 1 ms, whichever is larger. On the reference source it MUST also stay at or under 50 ms. A query that gets faster is always acceptable.
- **FR-008**: The target is one built graph of the reference source taking at most a third of the memory measured at the start of this work (FR-002). On 2026-10-26 that measurement gave 43.5 MiB, so the target is then about 14.5 MiB; the issue's 16 MiB was a third of its earlier 47.9 MiB.
- **FR-009**: If the schema chosen by FR-005 is not smaller than today's, the schema MUST NOT change, and the work MUST deliver the measurements that show why. If it is smaller but misses the target of FR-008, it MUST still ship, and the pull request MUST say how far it is from the target and what stood in the way.

**Integrity**

- **FR-010**: A graph that lists the same node `id` twice in one node table MUST be refused at build time, with a message that names the duplicated `id`, whether or not primary keys remain.
- **FR-011**: The refusal of FR-010 MUST reach a Maxitor user the same way as any other source that cannot be built, and MUST leave nothing stored for that source.
- **FR-012**: A test MUST build a graph with a duplicated node and prove it is refused.

**Regression guard**

- **FR-013**: The test suite MUST include a test that builds one test graph and checks two independent things:
  - **the shape of the schema**: the built database has exactly the indexes and primary keys the change decided to keep (none, if the expected variant ships), read from the database's own catalogue. Any index or primary key added back, under any name, fails it.
  - **the memory**: the total memory of the build stays at or under a ceiling set between the memory after the change and before it, with a margin that does not fail on noise.

  The test's documentation MUST say that the ceiling was measured on the maintainer's machine with the locked database version, and that only the local check run executes it: CI does not run the test suite today. If FR-009 leaves the schema unchanged, this test is not added.

**Linux memory**

- **FR-014**: The process-size sequence of the issue (0, 1, 5, 10 graphs held, all dropped, 3 built again) MUST be measured in the stand's container image and recorded.
- **FR-015**: If memory is not returned to the system after graphs are dropped, the documentation of the store's limits MUST say that the process size is the peak of graphs held at once, and MUST say whether a setting of the database changes it.

**Tail**

- **FR-016**: The work MUST end with the three steps of Principle VI, in order: the check run taken to zero, the documentation, one changelog article.

### Key Entities

- **Built graph**: what Maxitor makes from one download of a source; its memory is the subject of this work.
- **Index**: an extra structure on a table that makes finding rows by a column fast, paid for in memory and build time. A primary key is an index that also refuses a second row with the same `id`.
- **Diagram queries**: the six reads under `/api/v1/` (`list-domains`, `list-entities`, `list-node-types`, `full-graph`, `lifecycle-finite-automaton`, `domain-use-case-diagram`) plus the sidebar build.
- **Measurement**: one run of FR-001 on one graph, with its memory and timing figures.
- **Index usage table**: for each index, the diagram queries that use it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One built graph of the reference source takes at most a third of its memory before the change. If it does not, the pull request shows how much was gained and why the rest is out of reach within FR-006 and FR-007, or, when nothing smaller was possible, that the schema stayed.
- **SC-002**: 100 % of diagram answers and sidebar answers on the graphs in the tests are byte for byte the same before and after.
- **SC-003**: No diagram query or sidebar build grows by more than 20 % or 1 ms (whichever is larger), and none takes more than 50 ms on the reference source.
- **SC-004**: A graph with a duplicated node is refused at build time in 100 % of runs, with the duplicated `id` in the message.
- **SC-005**: The process-size sequence on the stand's Linux image is in the documentation, with a plain answer to "does memory come back after graphs are dropped".
- **SC-006**: The process size gained per held graph of the reference source (FR-004) falls by at least half. On the 2026-10-26 measurement on macOS it was 54.3 MiB per graph today and 22.0 MiB without primary keys and indexes, so 50 graphs would take about 1.1 GiB instead of 2.7 GiB. This is computed from 10 graphs, not measured with 50; the stand's own figure is what FR-014 measures.
- **SC-007**: Putting back any primary key or any index, including the 2 `state` indexes, makes the guard test of FR-013 fail.

## Assumptions

- The reference source is the one the issue names; its size has changed since the issue was written. "Before" and "after" are measured on the copy saved on 2026-10-26, kept in this feature's folder as `data/ref-graph-2026-10-26.json.gz` (SHA-256 of the uncompressed bytes `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`), so the comparison stays reproducible if the source changes again.
- The largest graph in the tests is the demo's graph (`aoa-demo`, 3 264 nodes and 4 907 edges, about seven times the reference source). It stands in for a larger service; no larger graph is generated for this work.
- Byte-for-byte equality of answers is proven by the existing payload tests plus a direct before/after comparison of every answer on the reference source and on the demo's graph.
- The database stays DuckDB; what an index costs and how memory is released are measured on the version the repository locks.
- The stand's container image is the one built from `packages/aoa-maxitor/Dockerfile`.

## Out of Scope

- The graph store of #214: its limit, its idle timeout, or how graphs are keyed.
- What the diagrams show.
- Replacing DuckDB.
- Refusing duplicated edges, or a node `id` repeated across different node tables.
