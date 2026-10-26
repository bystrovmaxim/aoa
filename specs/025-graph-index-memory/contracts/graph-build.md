# Contract: Building a Graph

## 1. `DuckDBGraphResource.build_from_json(payload)`: unchanged signature

| Input | Before | After |
|---|---|---|
| a valid graph | returns a resource | returns a resource; every query answers byte for byte the same |
| one node `id` twice **in one node table** | raises `duckdb.ConstraintException`: `Constraint Error: Duplicate key "id: <id>" violates primary key constraint.` | raises `ValueError`: `Graph has a duplicate node id "<id>" in table "<table>".` |
| one `id` in **two different** node tables | returns a resource | returns a resource (unchanged; clarified scope) |
| a duplicated edge | returns a resource | returns a resource (unchanged) |
| an empty graph | returns a resource | returns a resource |

When several ids are duplicated, the message names the first one in table-name, then id, order, so the same payload always gives the same message.

## 2. Through Maxitor

`GraphStore` wraps any build exception in `GraphBuildError(str(exc))`. A graph read for a source whose payload has a duplicate is refused like any other source that cannot be built: the existing 422 answer, whose reason is the message above. Nothing is stored for that source, and the store's 10-second failure memory applies, as for any failed build. The HTTP contract of #214 (`specs/024-graph-per-source/contracts/graph-source-http.md`) does not change.

## 3. Measurement helper (test tooling, not product)

Run from `packages/aoa-maxitor`:

```text
python -m tests.graph_build_metrics <graph-json URL | path to a .json or .json.gz file> [--runs N] [--explain] [--rss-sequence]
```

The argument is either a service's `graph-json` envelope or a bare coordinator payload; both are accepted. The output is one JSON object on stdout:

```json
{
  "source": {"ref": "…", "sha256": "a9d73e90…", "bytes": 326063, "nodes": 440, "edges": 550},
  "memory_mib": {"ART_INDEX": 38.0, "IN_MEMORY_TABLE": 5.26, "OVERFLOW_STRINGS": 0.25, "total": 43.51},
  "rss_per_graph_mib": {"method": "ps", "before": 69.0, "after_10": 612.0, "per_graph": 54.3},
  "build_ms": 120.0,
  "query_ms": {"full-graph": 5.2, "list-domains": 0.0, "…": 0.0, "sidebar": 0.0},
  "fingerprints": {"full-graph": "sha256…", "list-entities:<domain id>": "sha256…"},
  "index_usage": {"ix_domain_edges_target": ["list-entities", "domain-use-case-diagram"], "ix_state_kind": []},
  "rss_mib": [{"step": "0 held", "rss": 75.0}]
}
```

`index_usage` is present only with `--explain`, and `rss_mib` only with `--rss-sequence`. The figures in the example are placeholders except the source, memory and process-size figures, which are the 2026-10-26 measurement on macOS. `sha256` is computed over the uncompressed bytes.
