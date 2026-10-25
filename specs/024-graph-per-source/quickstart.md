# Quickstart: validating one graph per source

**Feature**: [spec.md](spec.md) · **Contract**: [contracts/graph-source-http.md](contracts/graph-source-http.md) · **Model**: [data-model.md](data-model.md)

## Prerequisites

- Repository environment: `uv sync`; client: `cd packages/aoa-maxitor/client && npm ci`.
- A reachable source. The reference one is `https://admingameoffer.aoa.run/graph-json`; tests use fixtures and stubbed downloads and need no network.

## 1. Automated proof

```bash
uv run pytest packages/aoa-maxitor/tests -q
```

Expected: the store tests (single flight, capacity, idle removal, failed build), the middleware tests (400, 422, 503, two interleaved clients, one graph per request), the load tests (reload replaces one source, a failed reload keeps the old one) and the burst test (300 simultaneous opens → 1 download, 1 build, 0 errors) pass.

```bash
cd packages/aoa-maxitor/client && npm test
```

Expected: the helper appends `source` and refuses without one; a deep link sends no `POST /api/load`; a typed source sends one; the button sends one and refetches.

## 2. The example

```bash
uv run python examples/step_26_maxitor/02_api_graph_per_source.py
```

Expected: every case from the contract printed with its real status and body — two sources side by side, a cold read, 400 without a source, 422 for an unbuildable source, an explicit reload, idle removal and rebuild, capacity eviction, one build for a burst.

## 3. In the browser

Run the API with the built client and open the deep link:

```bash
MAXITOR_GRAPH_IDLE_SECONDS=60 uv run maxitor-api
```

`http://127.0.0.1:8101/?source=https%3A%2F%2Fadmingameoffer.aoa.run%2Fgraph-json&view=full-graph`

Check, with the network panel:

1. The deep link draws the graph; no `POST /api/load` is sent, and every graph read carries `source=`.
2. "Reload from service" sends exactly one `POST /api/load`, then the sidebar and the diagram again; URL and selected diagram stay; the button is disabled while it runs.
3. Wait more than 60 s, click a diagram: it shows, after one slower answer, with no error and no prompt.
4. Open a second deep link to another source in a second tab; clicking in each tab keeps showing its own graph.
5. Leave the source: nothing is sent.
