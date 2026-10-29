# Contract: Maxitor's web part is `front`

| Before | After |
|---|---|
| `packages/maxitor/app/` | `packages/maxitor/front/` |
| `packages/maxitor/app/src/maxitor/viewer/` | `packages/maxitor/front/src/maxitor/front/` |
| `maxitor.viewer` (imports, ids in the graph) | `maxitor.front` |
| `pip install "maxitor[viewer]"` | `pip install "maxitor[front]"` |
| command `maxitor-api` (`maxitor.viewer.launch:viewer`) | command `maxitor` (`maxitor.front.launch:main`) |
| `packages/maxitor/app/graph.json` | `packages/maxitor/front/graph.json` |
| `graph-builder.toml` entry `maxitor`, build `python -m maxitor.viewer.build_graph` | build `python -m maxitor.front.build_graph`, file `packages/maxitor/front/graph.json` |
| the hint `maxitor-api needs the viewer: pip install "maxitor[viewer]"` | `maxitor needs its front: pip install "maxitor[front]"` |

Kept: old specs and past changelog entries. The old-name test fails on any of `maxitor.viewer`, `maxitor/viewer`, `maxitor[viewer]`, `packages/maxitor/app`, `maxitor-api` elsewhere.
