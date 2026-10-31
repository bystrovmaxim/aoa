# Contract: Maxitor API

## `GET /api/v1/lifecycle-finite-automaton`

Existing action, same parameters and rules of keys and logs (spec 037). A read of A goes as the use-case read does, with A's source and key.

The answer gains two fields, and nothing else changes:

```json
{
  "lifecycle_finite_automaton": {
    "states": [{ "id": "a.Offer:lifecycle:status:open", "key": "open", "...": "as today" }],
    "transitions": [{ "id": "a.Offer:lifecycle:status:open|lifecycle_transition|a.Offer:lifecycle:status:done|open", "source": "open", "target": "done" }]
  }
}
```

- `id` is the protocol's, read from the graph.
- A lifecycle the version does not hold stays refused as today; the client asks the left panel first.

No other endpoint is added. The comparison reads are spec 038's.
