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