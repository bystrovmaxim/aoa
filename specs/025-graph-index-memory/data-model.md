# Data Model: A Built Graph Without the Indexes It Does Not Need

Nothing here is stored by the product except the graph schema itself; the other entities are what the measurement produces.

## Graph schema (production)

- **21 node tables**, one per node type branch of the graph JSON schema; each has `id VARCHAR NOT NULL`. Today `id` is also `PRIMARY KEY`.
- **31 edge tables** (`*_edges`), each with `source_id`, `target_id`, `relationship`, `is_dag` and type-specific columns. Today each has two indexes, `ix_<table>_source` and `ix_<table>_target`.
- **`state`** additionally has `ix_state_lifecycle (lifecycle_class_id, state_key)` and `ix_state_kind (kind)`.
- **Views** `nodes`, `edges`, `nodes_type_counts`, `edge_type_counts` — unchanged.

**Invariant (kept)**: an `id` is unique within its node table. Enforced today by the primary key; after phase 4/5 by the duplicate check below. An `id` repeated across two node tables is accepted, as today.

**Catalogue (what the guard reads)**: today `duckdb_indexes()` lists the 64 explicit indexes, and `duckdb_constraints()` lists 21 `PRIMARY KEY` and 228 `NOT NULL`. In the expected variant there are no indexes, and only the 228 `NOT NULL` remain.

## Duplicate check

- **When**: after all rows are loaded, before the views are created.
- **What**: one query over the 21 node tables returning the first `(table, id)` that occurs more than once in its table, in a stable order (table name, then id).
- **Outcome**: none found → the build continues; one found → `ValueError` with the message in [contracts/graph-build.md](contracts/graph-build.md); no resource is returned, so the store keeps nothing.

## Schema variant

One way of building the schema, measured as a whole build (research R1).

| Field | Meaning |
|---|---|
| name | `today`, `no-index`, `no-primary-key`, `none`, or a named mix decided in phase 3 |
| primary keys | which node tables keep `PRIMARY KEY` |
| indexes | which of the 64 indexes are created |

## Measurement

One run of the helper on one graph and one schema.

| Field | Meaning |
|---|---|
| source | URL or file the graph was read from, and its byte size, node count, edge count |
| memory | MiB per `duckdb_memory()` tag, and their total, on a fresh build |
| process size per graph | process size before and after building and holding 10 graphs in one process, and the gain per graph (FR-004); the method (`VmRSS` or `ps`) is named |
| build time | median build time over the runs |
| query medians | per diagram query and the sidebar build: median ms; for queries with a parameter, the slowest domain or lifecycle |
| fingerprints | per query and parameter: SHA-256 of the canonical JSON of the answer — equal fingerprints before and after prove FR-006 |

## Index usage

For each primary key and index: the queries whose `EXPLAIN` plan reads through it. An entry with no query is *unused*. Written to `index-usage.md` and posted to the issue.

## RSS sequence (Linux)

Process size (`VmRSS`, MiB) after each step: 0, 1, 5, 10 graphs held; all dropped plus `gc.collect()`; 3 built again — once with DuckDB defaults, then once per allocator setting tried.
