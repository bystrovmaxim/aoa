# Open Gnomon Protocol — frozen copies

The Open Gnomon Protocol, the language of a system's graph, lives in [bystrovmaxim/gnomon](https://github.com/bystrovmaxim/gnomon/tree/main/packages/open-gnomon-protocol), together with Maxitor, the viewer that reads it.

The files in `graph/` stay here because each published schema names its own address as its `$id` — `https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/open-gnomon-protocol/graph/<version>.json` — and a published version never changes. They are byte for byte the versions gnomon publishes, never edited here; a new version of the protocol appears in gnomon, not in this folder.

AOA writes its graph by version 1.5: [`graph_json_schema.json`](../aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.json) beside the graph code is its copy.
