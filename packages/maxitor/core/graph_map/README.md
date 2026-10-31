# graph_map — a graph of the Open Gnomon Protocol as a map

Part of the [`maxitor`](../../README.md) package. It needs nothing beyond the standard library, and imports nothing of AOA, Maxitor's app or a tool.

It cuts a graph document into areas, one per domain and one for everything outside domains; writes the DOT that Graphviz lays each area out from, and reads the answer; keeps each area's place on the map; and assembles the overview and each area's detail. It runs no process: whoever calls it runs `sfdp`.

| Module | What it does |
|---|---|
| `areas.py` | Areas, a node's home, its level, an area's content hash |
| `layout.py` | The DOT of an area, and reading `sfdp -Tjson0` |
| `places.py` | Where each area stands: places are kept, so one area's change moves no other |
| `assemble.py` | The overview, with counts, bundles and sketches, and each area's detail |

To run `sfdp` locally, install Graphviz:

```bash
brew install graphviz
```

The Docker image installs it.
