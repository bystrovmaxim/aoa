# Contract: `maxitor.graph_compare`

Standard library only; imports nothing of AOA, Maxitor's app or a tool (research R2).

```python
from maxitor.graph_compare import compare, Status, Change, GraphNotComparableError

result = compare(older_document, newer_document)   # parsed JSON objects

result.node_counts            # Counts(added=2, removed=0, changed=1)
result.edge_counts            # Counts(added=13, removed=1, changed=2)
result.nodes["gameoffer.offers.OfferRequestItemDetailEntity"].status   # Status.CHANGED
result.edges["gameoffer.offers.OfferRequestCoreEntity|entity_relation|chosen_offer"].differences
# (Difference(path=("target_id",), change=Change.CHANGED,
#             before="gameoffer.offers.OfferCoreEntity",
#             after="gameoffer.offers.OfferRequestItemDetailEntity"),)
```

## Input

Two graph documents of the Open Gnomon Protocol, `schema_version` `"1.0"` or `"1.1"`, each an object with `nodes` and `edges` lists. They need not be valid against the schema beyond what comparing needs: a string `id` on every node, and on every `1.1` edge; on a `1.0` edge, the strings the id rule reads.

## Output

See [data-model.md](../data-model.md#the-comparison-maxitorgraph_compare-standard-library-only). Every node id and every edge id of A and B is a key exactly once.

## Refusals — `GraphNotComparableError`

| Case | Message names |
|---|---|
| `schema_version` other than `1.0`, `1.1` | the version |
| `nodes` or `edges` missing or not a list | which |
| an element without a string `id` (a `1.1` edge, any node) | its position and kind |
| two nodes, or two edges, with one id | the id |
| a `1.0` edge whose id cannot be computed | the edge type and the field |

## `graph_builder.differences` over it (research R3)

`differences(old, new, limit=20)` keeps its output line for line:

```text
nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
edges[id=…|application|…]: added
… and 7 more
```
