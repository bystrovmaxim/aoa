# graph_compare — two graphs of the Open Gnomon Protocol, compared by `id`

Part of the [`maxitor`](../../README.md) package: `pip install maxitor` with no extra installs it. It needs nothing beyond Python's standard library and knows nothing about AOA or any language.

```python
import json
from maxitor.graph_compare import compare

older = json.load(open("graph-0.8.0.json"))
newer = json.load(open("graph-0.9.0.json"))
result = compare(older, newer)

result.node_counts        # Counts(added=2, removed=0, changed=1)
result.edge_counts        # Counts(added=13, removed=1, changed=2)
for edge_id, item in result.edges.items():
    if item.status == "changed":
        for difference in item.differences:
            print(edge_id, ".".join(difference.path), difference.before, "→", difference.after)
```

## What it gives

Two documents — A the older, B the newer — wherever they come from: a [`repo-graph-port`](../../tools/repo_graph_port/README.md), a file, `git show`. The protocol says revisions are compared by `id`, never by position; `compare(a, b)` is that comparison:

- **every node and every edge gets exactly one status**: `added` (in B only), `removed` (in A only), `changed` (in both, something differs), `unchanged`. A rename is a removal plus an addition: identity is the `id`.
- **a changed element lists every difference by its property path**, from the element's top down to the leaf that differs — `("label",)`, `("target_id",)`, `("properties", "json_schema", "properties", "erid", "type")` — each `added`, `removed` or `changed`, with the value in A and in B. Every field but `id` is compared; a list is one value.
- **the counts**: added, removed, changed, for nodes and for edges.

`result.nodes` and `result.edges` hold A's ids in A's order, then the ids only B has.

## A relation that points elsewhere

An `entity_relation` edge is named by its field (`<entity>|entity_relation|<field>`), so a field that starts pointing at another entity keeps its id: it is one **changed** edge whose difference is `target_id`, old → new — never a removal and an addition.

## Graphs of version 1.0

A `1.0` graph's edges carry no `id`. Each gets the id a `1.1` graph would write for it (`<source_id>|<type>|<target_id>`; `entity_relation` by its field; `lifecycle_transition` with the state it leaves), so a `1.0` graph compares with a `1.1` one.

## Refusals

`GraphNotComparableError`, naming the side (`Graph A` / `Graph B`) and the cause, for: a `schema_version` other than `1.0` and `1.1`; a missing `nodes` or `edges` list; an element that is not an object or has no string `id`; two nodes, or two edges, with one id; a `1.0` edge whose id cannot be computed (the message names the edge type and the field).

## Who uses it

- `graph-builder check` names a stale file's differences with it.
- Maxitor's server compares two versions of a history with it and draws the result.

## Tests

```bash
uv run pytest packages/maxitor/core/graph_compare/tests -q
```

They cover every status, a retargeted relation, nested paths, lists, renames, `1.0` against `1.1`, each refusal, that the part imports only the standard library, and that two versions of the AOA demo's graph (3 213 nodes) compare in under a second.
