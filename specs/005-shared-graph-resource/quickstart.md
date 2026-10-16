# Quickstart — proving the feature works

**Feature**: `specs/005-shared-graph-resource` · **Date**: 2026-10-16

How to convince yourself, in this order, that Maxitor now declares one shared coordinator graph and
that nothing else about it changed. Every command is run from the repository root. Nothing here
needs network access, a running AOA service, or a built client.

The baseline figures quoted below were measured on this branch **before** the change, so the
"unchanged" claims have something to be compared against rather than being asserted.

---

## 0. Prerequisites

```bash
uv sync                       # the workspace, once
uv run pytest packages/aoa-maxitor -q
```

**Expected before the change**: `115 passed, 1 skipped in ~1.5s`.
**Measured after Phases 2–4** (the holder, the two test modules and the failure tests):
`134 passed, 1 skipped, 1 xfailed` — the 115 baseline plus the 20 cases this feature adds, with **no
existing test edited** (SC-011). The `xfailed` is not a passing grade: it is the one recorded
baseline that no longer holds, pinned so it cannot change unnoticed. See § 1.

If the existing suite is not green before you start, stop: this feature's acceptance is measured
relative to that baseline.

---

## 1. What the six routes answer with nothing loaded

Measured on the unmodified branch and on this one, with the lifespan running:

| Route | Before | After |
| --- | --- | --- |
| `GET /api/v1/list-domains` | `500 {"detail":"Internal server error"}` | unchanged |
| `GET /api/v1/list-entities` | `500 {"detail":"Internal server error"}` | **`200 {"domain_slices":[]}`** |
| `GET /api/v1/list-node-types` | `500 {"detail":"Internal server error"}` | unchanged |
| `GET /api/v1/full-graph` | `500 {"detail":"Internal server error"}` | unchanged |
| `GET /api/v1/lifecycle-finite-automaton` | `422` — required query parameter missing | unchanged |
| `GET /api/v1/domain-use-case-diagram` | `422` — required query parameter missing | unchanged |

**The one difference, and why it is not a bug in the tests.** `resolve_connections` used to call the
per-call factory eagerly and demand a `BaseResource` back, so every route failed before its action
ran. A ready resource always resolves, so the refusal now happens at the **first read** — and
`/api/v1/list-entities` with no `domain_qualnames` never reads the graph at all; it short-circuits
to an empty result. With a filter, the same route reads the graph and fails exactly as before. The
argument and the decision it needs are in [research.md](./research.md) R11.

```bash
uv run pytest packages/aoa-maxitor/tests/test_api_diagram_routes.py -q -k without_a_graph
```

The five unchanged routes are asserted as passing tests. The one divergence is a **strict `xfail`**:
if the old answer ever comes back, the test turns into an unexpected pass and fails loudly.

---

## 2. Before a load, the failure names the situation

`TestClient` **cannot** be used for this step. The adapter's `_CatchAllErrorsMiddleware` catches every
uncaught exception and answers one generic body without logging it, so the message never reaches a
caller or a log — measured, see [research.md](./research.md) R8. Drive the resource directly:

```python
from fastapi import FastAPI
from aoa.action_machine.exceptions import HandleError
from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder

app = FastAPI()
try:
    DuckDBGraphHolder(app).service
except HandleError as exc:
    print(exc)
```

**Expected**: `Graph is not loaded: call POST /api/load first.` — and **not**
`PerCallConnection factory for key 'DuckDBGraph' must return BaseResource, got 'NoneType'` (FR-007,
FR-008). The same message must appear when the application has started and nothing has been loaded
(`app.state.duckdb_graph = None`), and when the lifespan has not run at all (no attribute).

---

## 3. With a graph loaded, all six routes read the same object

```python
from fastapi.testclient import TestClient
from aoa.maxitor.api.app import create_app
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

app = create_app()
app.state.duckdb_graph = DuckDBGraphResource.build_from_json({
    "schema_version": "1.0",
    "nodes": [{"id": "d.x.Dom", "label": "X", "type": "Domain",
               "properties": {"name": "X", "description": ""}}],
    "edges": [],
})
client = TestClient(app)
print(client.get("/api/v1/list-domains").status_code, client.get("/api/v1/list-node-types").status_code)
```

**Expected**: `200 200`, with the payloads the same routes produced before the change (FR-014,
SC-001). Two consecutive requests — to the same route or to two different routes — must read **one
and the same** graph object (SC-003; the identity half is asserted on the holder, see
[research.md](./research.md) R5).

The same claim as a test, so it can be run rather than read:

```bash
uv run pytest packages/aoa-maxitor/tests/test_api_diagram_routes.py -q -k with_a_graph
```

---

## 4. A reload is seen by the next read

Replace `app.state.duckdb_graph` with a second graph and call **every one of the six** routes again.

**Expected**: each read returns the **second** graph's data, not the first's (SC-005). The holder
resolves on every read and caches nothing (FR-005), and no route holds a graph of its own.

```bash
uv run pytest packages/aoa-maxitor/tests/test_api_diagram_routes.py -q -k replaced_slot
```

---

## 5. The resource has no lifecycle

```bash
uv run pytest packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py -q -k lifecycle
```

**Expected**: the holder exposes no `open`, `close`, `begin`, `commit` or `rollback`,
`get_wrapper_class()` returns `None`, and a request through a route completes without any wrapper
being constructed (FR-009, SC-009; why absence is the measurable form, see
[research.md](./research.md) R6).

---

## 6. Nothing outside Maxitor's API layer moved

```bash
git status --short            # uncommitted work, while the phases are not committed yet
git diff HEAD --stat          # the same, counted against the last commit
git diff --stat main...HEAD   # everything this branch adds, once the phases are committed
```

**Expected**: changes confined to `packages/aoa-maxitor/src/aoa/maxitor/api/`,
`packages/aoa-maxitor/tests/`, `examples/step_26_maxitor/` (added by the closing documentation step)
and the package changelog. In particular **zero** files under `packages/aoa-action-machine/`,
**zero** edits to the six actions' `@connection` declarations, and nothing under
`packages/aoa-maxitor/client/` (FR-010, FR-012, FR-013, SC-010). The `uv.lock` release-sync commit
already on this branch is expected here and belongs to the release, not to this feature.

`git diff` alone is not enough at either moment: while the phases are uncommitted it prints nothing
(it compares against the index), and once they are committed it compares against `HEAD`, which is
the last phase. Use `git diff HEAD` before committing and `main...HEAD` after.

---

## 7. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: a green run, with two remarks standing and no others — the Vite chunk-size advisory
and LangGraph's pending-deprecation warning, both named in the constitution's check-run section as
accepted. Every other remark is fixed before the change is considered finished (Principle VI).

---

## What "done" looks like

- The existing Maxitor suite still passes with no edited test, plus the two new test modules.
- Five of the six routes return the measured baseline for "nothing loaded", and all six return their
  usual JSON for any loaded graph — including after a reload. The sixth route's one difference is
  pinned by a strict `xfail` and awaits a decision (§ 1, [research.md](./research.md) R11).
- Reading the shared resource without a graph raises `HandleError` naming the situation, in all
  three slot states.
- A `POST /api/load` that fails leaves the graph loaded before it in place for all six routes.
- Nothing under `packages/aoa-action-machine/` changed.
- `examples/step_26_maxitor/02_api_shared_graph.py` and its notebook run and show the cases.
- `bash scripts/run_checks_with_log.sh` is green.
