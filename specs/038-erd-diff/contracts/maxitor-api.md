# Contract: Maxitor's server for comparisons

Both reads are AOA actions behind Maxitor's `FastApiAdapter`, under `/api/v1/`, so `GraphSourceMiddleware` guards them (research R8): `source` is B, `a` is A, both a history's version sources or Live's source; the key, for a private history, only in `X-Maxitor-History-Key`. Every refusal of spec 037 applies to each of the two, in the order `a`, then `source`.

## `GET /api/v1/compare?source=<B>&a=<A>` — `CompareVersionsAction`

```json
{
  "counts": {"nodes": {"added": 2, "removed": 0, "changed": 1},
             "edges": {"added": 13, "removed": 1, "changed": 2}},
  "nodes": {"gameoffer.offers.OfferRequestStateEntity": "added",
            "gameoffer.offers.OfferCoreEntity:is_activated": "removed",
            "gameoffer.offers.OfferRequestItemDetailEntity": "changed"},
  "edges": {"gameoffer.offers.OfferRequestCoreEntity|entity_relation|chosen_offer": "changed"}
}
```

Only elements that are not unchanged are listed (research R10).

## `GET /api/v1/compare-element?source=<B>&a=<A>&kind=node|edge&id=<id>` — `CompareElementAction`

```json
{
  "status": "changed",
  "differences": [
    {"path": ["target_id"], "change": "changed",
     "before": "gameoffer.offers.OfferCoreEntity", "after": "gameoffer.offers.OfferRequestItemDetailEntity"}
  ]
}
```

`before` is absent for `added`, `after` for `removed`. An id in neither version → `404 {"detail": "not found"}`.

## Refusals added

| Case | Status | Body |
|---|---|---|
| `a` missing on a compare read | `400` | `{"detail": "Missing query parameter 'a': name the older version this comparison is from."}` |
| one of the two graphs cannot be compared (`GraphNotComparableError`) | `422` | `{"detail": "<which version>: <the reason>"}` |
| `kind` not `node` or `edge` | `400` | the adapter's validation answer |

## Changed

- `GraphEntry` holds `document` (research R7).
- `SetRoomVersionAction` takes `a` (research R14); see [room-protocol.md](room-protocol.md).

## Logs

Nothing new names an address or a key; a comparison computed is logged on the `debug` channel as `Comparison computed in <ms> ms: nodes +<added> −<removed> ~<changed>, edges +… −… ~…`.
