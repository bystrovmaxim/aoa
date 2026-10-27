# Contract: graph interchange and HTTP changes

## `graph-json` (`aoa-action-machine`)

`EntityField` node properties:

```json
{ "field_type": "str | None", "field_annotation": "UnionType[str, NoneType]", "primary_key_hint": false }
```

- `field_type` — the clean label by the FR-030 table of the spec.
- `field_annotation` — **new**, the full annotation as `field_type` read before. Consumers that need the exact type read this one.

Entity relation edge properties gain `optional`:

```json
{ "field_name": "customer", "relation_type": "association", "cardinality": "one", "optional": true, "…": "…" }
```

## `GET /api/v1/list-entities` (Maxitor)

Each field gains `annotation`; each relation's `source_cardinality` / `target_cardinality` is one of `one`, `zero_one`, `zero_many`, `one_many`. A reference line to a dictionary is `zero_many` at the referring table (`source`) and `one` at the dictionary (`target`).

## `GET /examples/model/graph-json` (Maxitor) — new

- Answer: `200`, `{"coordinator_json": "<Maxitor's own interchange JSON>"}`, served by `GetOwnGraphJsonAction` through `OwnModelGraphResource`.
- `ETag: "<first 32 hex of SHA-256 of the body>"`; a request with `If-None-Match` equal to it gets `304` with no body (adapter `ConditionalGetMiddleware`, unchanged).
- Needs no `source` (outside `GraphSourceMiddleware`).

## `GET /examples/model/graph-json` (demo)

Unchanged route; with `aoa-fastapi-adapter>=1.3.0` it answers with an `ETag` and `304` like the above.
