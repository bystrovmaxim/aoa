# Quickstart: validating events in the graph

Run from the repository root.

1. **Modes**: build a graph with one domain per mode and compare it with the table in [spec.md](spec.md) FR-006. Expected: exactly those nodes and edges.
2. **Schema**: `graph-builder check` on the regenerated files. Expected: `ok 1.3: …` for each.
3. **Older schemas**: `git diff main -- packages/open-gnomon-protocol/graph/1.0.json packages/open-gnomon-protocol/graph/1.1.json packages/open-gnomon-protocol/graph/1.2.json`. Expected: empty.
4. **Build refusal**: add to a mode 3 domain's method an event outside `events`. Expected: `EventContractError` naming the action, the method, the event and the domain.
5. **Comparison**: compare two graphs differing by one event and one `@emits` edge. Expected: those elements as added, and as removed the other way round.
6. **Maxitor**: open `packages/aoa-demo/graph.json`. Expected: it loads, events are on the full graph, the other diagrams are as before.
7. **Unknown version**: open a document with `schema_version` `9.9`. Expected: refused by every consumer.
