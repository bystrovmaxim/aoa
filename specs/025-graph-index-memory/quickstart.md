# Quickstart: validating issue #268

All commands start from the repository root.

## 1. Graphs to measure

The reference graph is committed: `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz`, the copy research R1 was measured on. Check it is intact:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && gunzip -c specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz | shasum -a 256
```

Expected: `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`.

The demo's graph is generated from the code. Research R8 records its SHA-256 and the commit it came from:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run python -c "from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator as b; open('/tmp/demo-graph.json','w').write(b().to_json())"
```

## 2. Measure (phase 2 and phase 5)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor && uv run python -m tests.graph_build_metrics ../../specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz --explain
```

Expected after the change, compared with `data/baseline-ref.json`:

- `memory_mib.total` at or under a third of the baseline (the target; FR-009 says what happens if it is missed);
- `rss_per_graph_mib.per_graph` at most half the baseline's;
- every `query_ms` within +20 % or +1 ms of the baseline, and at or under 50;
- every `fingerprints` value equal to the baseline's.

Repeat with `/tmp/demo-graph.json` against `data/baseline-demo.json`.

## 3. Tests

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run pytest packages/aoa-maxitor/tests -q
```

Must pass, including `test_duckdb_duplicate_node_id.py` and `test_duckdb_graph_memory.py`.

## 4. Adversarial checks

- Put `PRIMARY KEY` back on the node tables → both assertions of `test_duckdb_graph_memory.py` fail, nothing else does.
- Put the edge-table `CREATE INDEX` statements back → both assertions fail.
- Put only the 2 `state` indexes back, or add one index under a new name → the shape assertion fails.
- Add a heavy structure that is not an index → the memory assertion fails.
- Remove the duplicate check (primary keys absent) → `test_duckdb_duplicate_node_id.py` fails, nothing else does.

Each break is restored after it is seen.

## 5. Linux (phase 6)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && docker build -f packages/aoa-maxitor/Dockerfile -t maxitor-268 .
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && docker run --rm -v "$PWD/specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz:/ref.json.gz:ro" -v "$PWD/packages/aoa-maxitor/tests:/repo/packages/aoa-maxitor/tests:ro" -w /repo/packages/aoa-maxitor maxitor-268 python -m tests.graph_build_metrics /ref.json.gz --rss-sequence
```

Expected: an `rss_mib` list for the issue's sequence. Its last two steps answer whether memory comes back after graphs are dropped.

## 6. Check run

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```

This is the only place the guard test runs: CI does not run pytest.
