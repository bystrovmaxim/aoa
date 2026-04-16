# Golden graph fixtures

## `logical_minimal.json` (G0)

Synthetic input under `input` and canonical `expected` vertices/edges for the
minimal logical-graph builder (`action_machine.graph.logical.build_from_g0_input`).

### Regenerating expected output

If you intentionally change the G0 builder or the schema, update `expected` in
the same PR:

1. Adjust `input` / builder code.
2. Run `uv run pytest tests/graph_logical_contract/test_g0_logical_minimal.py -q`.
3. If the new graph is correct, update the `expected` block (keep vertices sorted
  by `id`, edges sorted by `source_id`, `target_id`, `edge_type`, `category`).

Optional: add a small script later (`python -m tools.dump_g0_golden`) to print
canonical JSON for copy-paste.

## `logical_test_domain.graph.json` (G2)

Canonical **logical** graph from `maxitor.test_domain.build.build_test_coordinator()`
after `get_logical_graph()`: sorted `vertices` (`id`, `vertex_type`) and `edges`
(`source_id`, `target_id`, `edge_type`, `category`). Used by
`tests/graph_logical_contract/test_pr5_g2_logical_test_domain_golden.py`.

The G2 test compares this file to a snapshot taken in a **fresh** ``python``
subprocess (see ``g2_snapshot_build_test_coordinator_clean_process``): pytest
pre-imports many modules, and graph discovery walks all loaded intent subclasses,
so an in-process ``build_test_coordinator()`` would drift from the golden that
was recorded for ``build._MODULES`` alone.

### Regenerating G2

When the narrow facet projection or test_domain declarations change **on purpose**:

1. From the repo root, run a small script that imports `_MODULES`, calls
   `build_test_coordinator()`, passes `coord.get_logical_graph()` through
   `g2_snapshot_from_logical_rx` from `tests/graph_logical_contract/logical_golden_dump`,
   wraps the result in `version` + `description`, and writes JSON with a trailing
   newline to `tests/fixtures/golden_graph/logical_test_domain.graph.json`.

2. Re-run `uv run pytest tests/graph_logical_contract/test_pr5_g2_logical_test_domain_golden.py -q`.

**G7** (reverse pairs for §5.3 types in `REVERSE_EDGE_MAP`) is asserted in
`test_pr5_g7_reverse_edge_pairs.py` against the live graph (not a separate JSON file).