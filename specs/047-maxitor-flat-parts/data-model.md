# Data Model: Maxitor parts one level shallower, and `front` named `web`

No stored data changes shape. The entities here are the five parts and the saved graph.

## Part

| Part | Before | After phases 1–2 | After phase 3 |
|---|---|---|---|
| web server and client | `front/src/maxitor/front/` | `front/maxitor/front/` | `web/maxitor/web/` |
| graph builder | `tools/graph_builder/src/maxitor/graph_builder/` | `tools/graph_builder/maxitor/graph_builder/` | same |
| history service | `tools/repo_graph_port/src/maxitor/repo_graph_port/` | `tools/repo_graph_port/maxitor/repo_graph_port/` | same |
| graph comparison | `core/graph_compare/src/maxitor/graph_compare/` | `core/graph_compare/maxitor/graph_compare/` | same |
| graph map | `core/graph_map/src/maxitor/graph_map/` | `core/graph_map/maxitor/graph_map/` | same |

Files under `src/` today, including `py.typed` and the JSON schemas: 102, 11, 41, 6 and 7, 167 in all. Line 1 changes in the 158 Python modules that carry a path.

**Rule**: no `maxitor/__init__.py` exists in any part, and none may appear, or the shared namespace breaks.

## Graph file

| File | After phases 1–2 | After phase 3 |
|---|---|---|
| `front/graph.json` | byte for byte the same | moves to `web/graph.json`, `maxitor.front` becomes `maxitor.web` |
| `tools/repo_graph_port/graph.json` | byte for byte the same | byte for byte the same |

**State change**: in the history of a graph, the commit of phase 3 reads as every `maxitor.front` node removed and a `maxitor.web` node created. It happens once.

## Extra

| Before | After |
|---|---|
| `front` | `web` |
| `all = ["maxitor[front]", "maxitor[repo-graph-port]"]` | `all = ["maxitor[web]", "maxitor[repo-graph-port]"]` |
