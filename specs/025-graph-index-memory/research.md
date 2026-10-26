# Research: A Built Graph Without the Indexes It Does Not Need

All figures were taken on 2026-10-26 on macOS with the repository's environment (DuckDB 1.5.6, Python 3.12). The reference source is `https://admingameoffer.aoa.run/graph-json` (326 063 bytes, 440 nodes, 550 edges), saved to a file so that every run reads the same bytes. That copy is kept as `data/ref-graph-2026-10-26.json.gz` in this folder (21 463 bytes compressed). SHA-256 of the uncompressed bytes: `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`.

## R1. What a built graph costs, by schema variant

**Measured.** Each variant was built in its own process, twice. Both runs gave the same bytes, so `duckdb_memory()` on a freshly built database is deterministic.

| Variant | Reference graph | Tiny test graph (4 nodes, 2 edges) |
|---|---|---|
| today: 21 primary keys + 64 indexes | **43.51 MiB** (indexes 38.0) | 4.74 MiB (indexes 3.5) |
| primary keys kept, the 64 indexes removed | **50.73 MiB** (indexes 10.25, tables 36.48) | 2.24 MiB |
| primary keys removed, the 64 indexes kept | 32.88 MiB (indexes 27.75) | 3.74 MiB |
| nothing: no primary key, no index | **13.38 MiB** | 1.24 MiB |
| nothing but one index (`ix_domain_edges_target`) | 14.38 MiB | — |

**Measured again, from outside the database.** One process builds 10 graphs of the reference source and keeps them; its size (`ps -o rss`) is read before and after.

| Variant | `duckdb_memory()` per graph | Process size gained per graph |
|---|---|---|
| today | 43.51 MiB | **54.3 MiB** (69 → 612 MiB) |
| nothing | 13.38 MiB | **22.0 MiB** (69 → 290 MiB) |
| nothing but one index | 14.38 MiB | 23.1 MiB |

So the database's figure falls 3.3 times, and the process's only 2.5 times. Each graph carries about 9–11 MiB that `duckdb_memory()` does not report: the connection, the catalogue, the allocator's reserve. That is why FR-004 measures the process before and after, and SC-006 is stated in it.

**The catalogue.** `duckdb_indexes()` lists the 64 explicit indexes today and none in the "nothing" variant. `duckdb_constraints()` lists 21 `PRIMARY KEY` and 228 `NOT NULL` today, and only the 228 `NOT NULL` in the "nothing" variant. Primary keys do not appear in `duckdb_indexes()`.

**Decision.** The decision is taken on whole-build variants, never by dropping an index from a built graph: `DROP INDEX` on a built database left `duckdb_memory()` unchanged in the same run (tiny graph, two indexes dropped, 3.5 MiB of indexes before and after).

**What this means for the plan.**

- The "nothing" variant meets FR-008: 13.38 MiB is under a third of 43.51 MiB (14.50 MiB), with about 1.1 MiB to spare.
- Removing only the 64 indexes makes a graph **larger**, not smaller: table memory jumps from 5.3 to 36.5 MiB. Why is not known. The plan does not depend on knowing it, because variants are compared as whole builds (FR-005). The result is recorded in the issue (plan phase 3, the issue's phase 2), because it rules out the obvious half-measure. The process-size measurement above confirms the direction of the main result from outside the database. It does not explain the jump.
- **The decision is close to settled before phase 3.** Every primary key must go: keeping them costs at least 10 MiB (43.5 against 32.9 MiB with the indexes, 50.7 against 13.4 MiB without). At most **one** small index fits under the target: one index gives 14.38 MiB against 14.50, two would not fit. Phase 3's `EXPLAIN` is still needed to prove that no query depends on an index. It changes the outcome only if an index is needed for the timing bound. Then FR-009 ships the smallest variant that keeps the timings, even above a third.

**Alternatives considered.** Measuring only the process size (RSS). Rejected as the only figure: it includes the interpreter and the allocator's reserve, never shrinks (R6), and needs 10 graphs to give a stable gain per graph. So the decision between variants uses `duckdb_memory()`, which is deterministic per build, and the process figure is reported beside it as the outside check (FR-004). It is also the figure for the Linux phase (FR-014).

## R2. Which queries can use an index at all

**Found in the code.** DuckDB joins tables by hashing them, not by looking rows up in an index. Its planner uses an index only for a scan filtered by a constant (`= ?`, a short `IN`). The diagram code has four such filters:

| Filter | Query | Index it could use |
|---|---|---|
| `domain WHERE id = ?` | `domain-use-case-diagram`, `list-entities` | primary key of `domain` |
| `lifecycle WHERE id = ?` | `lifecycle-finite-automaton` | primary key of `lifecycle` |
| `domain_edges WHERE target_id = ?` | `domain-use-case-diagram`, `list-entities` (4 places) | `ix_domain_edges_target` |
| `lifecycle_contains_state_edges lcs … WHERE lcs.source_id = ?` (states, and transitions joined through it) | `lifecycle-finite-automaton` (2 places) | `ix_lifecycle_contains_state_edges_source` |

Nothing filters `state` by `kind` or by `lifecycle_class_id`, so `ix_state_kind` and `ix_state_lifecycle` look unused.

**Measured later, and it went further (R2a, 2026-10-26).** Phase 3 read every statement of the seven actions under `EXPLAIN (FORMAT JSON)`: 96 statements (72 distinct plans) on the reference and 941 (823) on the demo. **No plan named any of the 21 primary keys or 64 indexes.** A synthetic probe confirmed it is not the small tables: equality, `IN` and `BETWEEN` filters on an indexed column, and a join with a dynamic filter, planned `SEQ_SCAN` on 200 000 and 2 000 000 rows, in memory and in a file database, with `index_scan_max_count` and `index_scan_percentage` raised. The full table is in `index-usage.md`; it is empty.

**Decision.** Phase 3 ran every query under `EXPLAIN` and recorded what the planner actually chooses (FR-003): nothing reads through an index. Phase 5 therefore removes all 21 primary keys and all 64 indexes; the expectation that up to two primary keys and two edge indexes might be used did not hold.

## R3. How fast the queries are, and what "slower" means

**Measured.** The full-graph query on the reference graph: 5.1–5.4 ms over 7 runs, one outlier at 10.9 ms. A build takes 0.1–0.3 s, depending on whether the interpreter has warmed up.

**Decision.** The clarified bound (FR-007): the median may grow by at most 20 % or by at most 1 ms, whichever is larger, and must stay at or under 50 ms. The median is taken over 21 runs after 3 warm-up runs. Queries that take a parameter (a domain, a lifecycle) run for **every** domain or lifecycle in the graph, and the slowest of them is the reported figure, so a parameter that happens to be cheap cannot hide a slow one.

**Where the timing is taken.** Through the action machine, with the built graph as the action's connection, the way the existing tests run the actions. That is the path a route takes, minus HTTP.

## R4. The largest graph in the tests

**Found.** The demo's graph (`aoa-demo`, `build_registered_interchange_coordinator()`, used in `packages/aoa-demo/tests/test_demo_dictionary_graph.py`): **3 213 nodes and 4 841 edges** (measured with the helper on 2026-10-26), about seven times the reference source. An earlier note said 3 264 and 4 907; that figure no longer matches the code. It stands in for a larger service (edge case "an index that matters only on a larger graph").

**Constraint.** `aoa-maxitor` does not depend on `aoa-demo`, and `scripts/check_package_boundaries.py` keeps it that way. The measurement therefore reads a graph from a URL or a JSON file, and the demo's graph is written to a file with a one-line command run from the workspace environment (see quickstart). Maxitor's tests never import the demo.

## R5. Refusing a duplicate node without primary keys

**Measured today.** A payload with one node twice fails the build with `duckdb.ConstraintException`: `Constraint Error: Duplicate key "id: actions.admins.sign_in_admin_action.SignInAdminAction" violates primary key constraint.` `GraphStore` turns any build exception into `GraphBuildError(str(exc))` (`graph_store.py:240` and `:268`), and the routes answer that with the existing refusal for a source that cannot be built.

**Decision.** After the rows are loaded, one small `GROUP BY` per node table, in table-name order, looks for an `id` that appears more than once **in the same table** (clarified scope: a repeat across tables stays accepted). If it finds one, the build raises `ValueError` naming the `id` and the table. The message replaces DuckDB's wording, for example: `Graph has a duplicate node id "actions.admins.sign_in_admin_action.SignInAdminAction" in table "action".` The store's existing wrapping carries it to the user unchanged (FR-011), and nothing is stored. The per-table loop replaced a single `UNION ALL` query over all 21 tables: the union retained about 6 MiB per held connection, the loop about 2.6 MiB (R9).

**Alternatives considered.**
- Checking in Python while filling the tables. Rejected: the fill code is spread over 21 `_fill_table_*` functions, and the database answers the question in one scan per table.
- A `UNIQUE` constraint. Rejected: it builds the same index as a primary key and costs the same memory.

The check's cost is part of the build time measured before (plan phase 2) and after (plan phase 5).

## R6. Memory after a graph is dropped, on Linux

**Known from the issue (macOS).** The process size does not drop when graphs are dropped. It stays at the peak and is reused.

**Approach.** Build the stand's image from `packages/aoa-maxitor/Dockerfile` (Docker is installed locally), run the issue's sequence inside it, and read the process size from `/proc/self/status` (`VmRSS`) at each step. The image is `python:3.12-slim`, which is Debian with glibc.

**DuckDB settings to try if memory is not returned.** DuckDB's allocator settings: `allocator_flush_threshold`, `allocator_bulk_deallocation_flush_threshold`, `allocator_background_threads`. Whether they exist in DuckDB 1.5.6, and whether they apply to the Linux build only, is to be checked against `SELECT * FROM duckdb_settings()` inside the image before they are tried. A process-level remedy (`malloc_trim` from glibc) may be noted in the documentation as an observation. It is not built here: the store of #214 is out of scope.

**If Docker cannot run the image.** The result says so and records what was measured instead (spec edge case).

## R7. The regression guard

**Decision (clarified, then strengthened by the review).** A test builds the tiny test graph and checks two independent layers.

1. **The shape of the schema**, read from the catalogue: `duckdb_indexes()` lists exactly the indexes the change keeps, and `duckdb_constraints()` lists exactly the primary keys it keeps. In the expected variant both lists are empty. This catches any index or primary key added back, under any name, including the 2 `state` indexes. A memory ceiling cannot catch those: they cost about 0.08 MiB on this graph.
2. **The memory**: total `duckdb_memory()` at or under a ceiling. On the R1 figures:
   - after the change: 1.24 MiB;
   - the smallest regressing variant: 2.24 MiB (primary keys back);
   - the ceiling sits halfway, at about 1.75 MiB.

   This layer catches a heavy structure that is not an index, which the first layer would miss.

Memory per fresh build is deterministic, also inside one process: two graphs built one after the other both report 4.738 MiB today. The ceiling is fixed with the numbers measured after phase 5, not with these.

**Where it runs.** CI (`.github/workflows/ci.yml`) builds the client and checks that Git is clean; it does not run pytest. The guard therefore runs only in the local check run (`scripts/run_checks_with_log.sh`). Its ceiling is in absolute MiB, measured on macOS with the locked DuckDB, and another platform may report slightly different figures. The test's docstring says both things, so whoever sees it fail elsewhere knows where the number came from (FR-013).

**Why the tiny graph.** It builds in milliseconds and is already written in the test suite. An index costs far less there than on the reference graph: about 0.04 MiB, against about 1 MiB measured for one index on top of the "nothing" variant (R1). That is why the shape layer, not the memory layer, is what catches a single index.

## R8. Baseline, measured through the helper

**Method.** `python -m tests.graph_build_metrics <graph>` from `packages/aoa-maxitor`: 21 timed runs per query after 3 warm-ups, with the slowest parameter reported per family; the process figure from ten graphs held in one process; the build time as the median of seven builds. Two full runs gave identical `memory_mib` and `fingerprints` (15 keys on the reference, 243 on the demo). Full reports: `data/baseline-ref.json` and `data/baseline-demo.json`.

| Figure | Reference | Demo |
|---|---|---|
| Source | `data/ref-graph-2026-10-26.json.gz`, SHA-256 `a9d73e90…f84cf`, 326 063 bytes, 440 nodes, 550 edges | `build_registered_interchange_coordinator()` at `fd10ed4b`, SHA-256 `54a5e91c…d488a4`, 2 708 885 bytes, 3 213 nodes, 4 841 edges |
| `ART_INDEX` | 38.00 MiB | 57.50 MiB |
| `IN_MEMORY_TABLE` | 5.26 MiB | 7.93 MiB |
| `OVERFLOW_STRINGS` | 0.25 MiB | — |
| **total** | **43.51 MiB** | **65.43 MiB** |
| Process size gained per graph | 53.4 MiB | 77.6 MiB |
| Build time, median of 7 | 125.3 ms | 850.8 ms |
| `list-domains` | 1.23 ms | 1.39 ms |
| `list-node-types` | 2.38 ms | 2.42 ms |
| `full-graph` | 5.86 ms | 19.83 ms |
| `sidebar` | 4.30 ms | 20.10 ms |
| `list-entities` (slowest domain) | 25.56 ms | 31.65 ms |
| `domain-use-case-diagram` (slowest domain) | 6.40 ms | 7.36 ms |
| `lifecycle-finite-automaton` (slowest lifecycle) | 4.42 ms | 6.57 ms |

The demo's figures are for the graph as it is at commit `fd10ed4b`; the SHA-256 makes it regenerable. It has 3 213 nodes and 4 841 edges, not the 3 264 and 4 907 that R4 used to say.

**The process figure's method.** The helper reads `VmRSS` on Linux and `ps -o rss=` elsewhere. The sandbox in which this baseline was taken does not permit `ps`, so the helper used its `getrusage` peak fallback; the method is named in the JSON as `getrusage-peak`. R1's `ps` figure for the same graph and schema was 54.3 MiB per graph, against 53.4 here, so the two agree.

**Timings are noisier than memory.** Two full runs of the demo differed by up to 30 % on `domain-use-case-diagram` (7.36 against 9.48 ms), while three isolated repeats of that family agreed at 7.1–7.2 ms. The table keeps the faster full run, and phase 5 compares the faster of three runs per graph, so a transient slow session cannot fake a regression. `memory_mib` and `fingerprints` did not move between runs.

## R9. After: the same graphs with no primary key and no index

**Measured.** The final build has 21 node tables with `id VARCHAR NOT NULL` and no `PRIMARY KEY`, no `CREATE INDEX`, and `_refuse_duplicate_node_ids` after loading. The same helper and the same saved graphs as R8:

| Figure | Reference before | Reference after | Demo before | Demo after |
|---|---|---|---|---|
| Memory total | 43.51 MiB | **13.38 MiB** | 65.43 MiB | **20.35 MiB** |
| — `BASE_TABLE` | — | 8.25 MiB | — | 11.50 MiB |
| — `IN_MEMORY_TABLE` | 5.26 MiB | 4.88 MiB | 7.93 MiB | 8.85 MiB |
| — `ART_INDEX` | 38.00 MiB | — | 57.50 MiB | — |
| Process size gained per graph | 53.4 MiB | **24.5 MiB** | 77.6 MiB | **32.0 MiB** |
| Build time, median of 7 | 125.3 ms | 108.8 ms | 850.8 ms | 750.5 ms |
| `list-domains` | 1.23 ms | 1.18 ms | 1.39 ms | 1.37 ms |
| `list-node-types` | 2.38 ms | 2.32 ms | 2.42 ms | 2.40 ms |
| `full-graph` | 5.86 ms | 5.96 ms | 19.83 ms | 19.70 ms |
| `sidebar` | 4.30 ms | 4.37 ms | 20.10 ms | 18.43 ms |
| `list-entities` (slowest domain) | 25.56 ms | 25.10 ms | 31.65 ms | 30.49 ms |
| `domain-use-case-diagram` (slowest domain) | 6.40 ms | 6.26 ms | 7.36 ms | 7.10 ms |
| `lifecycle-finite-automaton` (slowest lifecycle) | 4.42 ms | 4.37 ms | 6.57 ms | 4.69 ms |

The target is met on both graphs: 13.38 is 30.8 % of 43.51 (target 14.50), and 20.35 is 31.1 % of 65.43 (target 21.81). The process figure falls by 54.1 % on the reference (53.4 → 24.5, target 26.7) and by 58.8 % on the demo (77.6 → 32.0). The build is faster as well (the 85 index structures are no longer created). Every fingerprint is unchanged: 15 of 15 on the reference, 243 of 243 on the demo. Every query is within FR-007's `max(20 %, 1 ms)` bound and under 50 ms.

**The duplicate check's own cost.** A single `UNION ALL` query over the 21 node tables retained about 6 MiB per held connection: the same 10-graph probe gave 27.9 MiB per graph, and a no-check build gave 21.9. Replacing it with one small `GROUP BY` per table, stopping at the first duplicate, keeps the required table-name-then-id order and lowers the figure to 24.5 MiB per graph (32.0 on the demo). That is the implementation that ships; the check looks at every node table and adds a few milliseconds to the build.

**The process figure's method.** The baseline was read with the `getrusage` peak fallback (53.4 MiB); the after figure is current RSS through `psutil`, because `ps` is not permitted in the sandbox (the helper prefers `/proc/self/status`, then `ps`, then `psutil`, then the peak). R1's `ps` figure for the same "nothing" variant was 22.0 MiB, so the two methods agree within their noise. On the stand's Linux image the helper reads `VmRSS`.

**The guard.** `tests/test_duckdb_graph_memory.py` asserts an empty `duckdb_indexes()` and no `PRIMARY KEY` in `duckdb_constraints()`, and a total at or under 1.75 MiB on the tiny graph (the build takes 1.24). The adversarial breaks were each seen and reverted: one index back fails the shape assertion, the 21 primary keys back fail both, a 300 000-row table that is not an index fails the memory assertion only, and removing `_refuse_duplicate_node_ids` fails three duplicate tests.
