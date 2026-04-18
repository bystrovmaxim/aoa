# Golden graph fixtures

## `synthetic_minimal.json`

`input` is an **opaque** interchange payload: top-level `vertices` and `edges`
lists (same row shape as coordinator interchange). Implemented in
`action_machine.graph.graph_builder` (`build_from_synthetic_bundle` / `GraphBuilder`):
unmarshal and validate ids/endpoints only — no derivation from domain/action tables.
`expected` is the synthetic bundle canonical graph. Facet-only goldens live in
`expected_from_facets` (full `_g0_facet_vertices()`), `expected_from_facets_meta_no_action`,
etc., for `test_graph_builder.py`.

### Regenerating expected output

When the canonical minimal graph changes on purpose, keep `input` and `expected`
in sync (tests compare facet builders to `expected` and the golden compares
`build_from_synthetic_bundle(input)` to `expected` using sorted lists).

## Samples interchange and DAG (no checked-in JSON)

`tests/graph_contract/test_golden_test_domain_graph.py` and
`test_golden_dag_subgraph_test_domain.py` assert **determinism**: two fresh
Python subprocesses each build `build_sample_coordinator()` and compare identical
G2-style vertex/edge lists or G4-style `dag_edges` / `acyclic_expected` payloads
(see `g2_snapshot_build_sample_coordinator_clean_process` and
`g4_snapshot_build_sample_coordinator_clean_process` in `tests/graph_contract/golden_dump.py`).
There is no committed snapshot file for those graphs.

Reverse pairs for §5.3 types in `REVERSE_EDGE_MAP` are asserted in
`test_reverse_edge_pairs.py` against the live graph (not a separate JSON file).

## GraphML / HTML export (smoke)

There is no separate XML golden file in this repository for export: GraphML/HTML smoke
tests live under ``tests/maxitor/test_export_uses_graph.py`` (substring checks
on generated files under ``tmp_path``).
