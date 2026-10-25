# Maxitor — unchanged and still green

**Date**: 2026-10-24
**Requirement**: FR-010, FR-011 — the graph carries no condition data, one edge per distinct role,
and the `AccessDecide` node remains the statement of an object rule; Maxitor is not edited.

## Command

```text
uv run --extra dev pytest \
  packages/aoa-maxitor/tests/test_duckdb_access_decide_type.py \
  packages/aoa-maxitor/tests/test_full_graph_payload_metrics.py -q
```

## Result

```text
11 passed
```

No Maxitor source was edited. The `AccessDecide` node still reaches DuckDB
(`test_duckdb_access_decide_type`), and the full graph payload still validates
(`test_full_graph_payload_metrics`) after the action node lost `guard`/`guard_reason` and the role
edge became a bare edge with empty `properties` — exactly what research R10 asserted: Maxitor reads
node properties generically and names no gate word, so removing the condition data leaves its
payload unchanged.
