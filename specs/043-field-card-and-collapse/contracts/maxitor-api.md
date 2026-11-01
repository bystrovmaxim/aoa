# Maxitor API: spec 043

## `GET /api/v1/element-card`

Query: `id`, a node's id. A link's card needs no read: the map holds its kind and ends. The version comes as on every graph read.

```json
{"id": "x.Entity:lifecycle:state", "type": "lifecycle", "label": "state", "description": null, "lifecycle_id": "x.Entity:lifecycle:state"}
```

An id the version does not hold answers 404. `lifecycle_id` is the id itself on a lifecycle, else `null`.

## `GET /api/v1/list-entities`

A field row gains `lifecycle_id`, `null` on any row that is not a lifecycle.
