# Contract: Open Gnomon Protocol 1.3

`graph/1.3.json` is `graph/1.2.json` with these changes and no others:

1. `schema_version` is `const "1.3"`; `$id` names the new file.
2. `vertex` gains `event`: a `row` with `type` `const "Event"` and empty `properties`.
3. `domain` requires a boolean `typed_events`.
4. `link` gains two definitions of their own, `emits` and `domain_event`: `type` `const`, `relationship` `const "Association"` and `const "Aggregation"`, `is_dag` `const false`, empty `properties`. They are the first edges whose nature the schema fixes; the edges of earlier versions stay as they are.

A `1.2` document is not a `1.3` one by changing its version, because `typed_events` is required.

Example:

```json
{"id": "shop.OrderCompletedEvent", "type": "Event", "label": "OrderCompletedEvent", "properties": {}}
{"id": "shop.ShopDomain", "type": "Domain", "label": "ShopDomain",
 "properties": {"name": "shop", "description": "Shop", "typed_events": true}}
{"id": "shop.ShopDomain|domain_event|shop.OrderCompletedEvent", "type": "domain_event",
 "source_id": "shop.ShopDomain", "target_id": "shop.OrderCompletedEvent",
 "relationship": "Aggregation", "is_dag": false, "properties": {}}
{"id": "shop.Place:finish|@emits|shop.OrderCompletedEvent", "type": "@emits",
 "source_id": "shop.Place:finish", "target_id": "shop.OrderCompletedEvent",
 "relationship": "Association", "is_dag": false, "properties": {}}
```

Consumers read `1.0` to `1.3` and refuse anything else.
