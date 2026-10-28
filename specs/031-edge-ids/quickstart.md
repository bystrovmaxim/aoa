# Quickstart: Checking That Every Edge Has an Id

Validation scenarios for [spec.md](spec.md). Run from the repository root with the repository's own environment.

## 1. The demo graph: ids present, unique, computable from the row (SC-001, SC-002, SC-004)

```bash
uv run python - <<'EOF'
import json
from collections import Counter
from aoa.action_machine.graph.edge_identity import edge_id
from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator

first = build_registered_interchange_coordinator().to_json()
graph = json.loads(first)
edges = graph["edges"]
ids = [e["id"] for e in edges]
print(graph["schema_version"], len(edges), "edges,", len(set(ids)), "distinct ids")
print("in id order:", ids == sorted(ids))
print("computed == written:", all(edge_id({k: v for k, v in e.items() if k != "id"}) == e["id"] for e in edges))
pairs = Counter((e["source_id"], e["type"], e["target_id"]) for e in edges)
print("repeating pairs:", sum(1 for n in pairs.values() if n > 1))
EOF
```

**Expected**: `1.1 4841 edges, 4841 distinct ids`, `in id order: True`, `computed == written: True`, `repeating pairs: 61`. A second run prints the same, and two exports of the same build are identical strings.

## 2. Refusals (User Story 2)

The tests of the coordinator cover both:

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/graph -k "edge_id or duplicate_edge" -q
```

**Expected**: a graph with two edges of one id fails with `DuplicateEdgeError`, naming both edges; a node id with `|` fails with `InvalidGraphError`, naming the node.

## 3. A 1.0 file compares with a 1.1 export (User Story 3, SC-003)

Done by hand on gameoffer's snapshots 005 (0.8.0) and 006 (0.9.0), downloaded to a scratch folder outside the repository:

```bash
uv run python - "$SCRATCH/g005.json" "$SCRATCH/g006.json" <<'EOF'
import json, sys
from aoa.action_machine.graph.edge_identity import edge_id
a, b = (json.load(open(p)) for p in sys.argv[1:3])
ea = {edge_id(e): e for e in a["edges"]}
eb = {edge_id(e): e for e in b["edges"]}
added, removed = set(eb) - set(ea), set(ea) - set(eb)
changed = [k for k in set(ea) & set(eb) if ea[k] != eb[k]]
print(f"edges +{len(added)} -{len(removed)} ~{len(changed)}")
EOF
```

**Expected**: `edges +34 -1 ~9`. The result goes into the pull request; the files are not committed.

## 4. Readers keep working (FR-012, SC-005)

```bash
uv run pytest packages/aoa-maxitor/tests -q
```

**Expected**: the suite passes unchanged; Maxitor's diagram answers for the demo graph are the same as before the change.

## 5. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: green, with only the two accepted remarks (the Vite chunk-size advisory and LangGraph's pending-deprecation warning).
