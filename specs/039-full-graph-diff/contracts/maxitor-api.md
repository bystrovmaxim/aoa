# Contract: `GET /api/v1/full-graph`

The address and the headers do not change. The answer's edges change their `id`, and its nodes gain one field:

```json
{
  "nodes": [{"id": "a.Entity", "data": {"label": "Entity", "title": "a.Entity", "node_type": "Entity", "type_slug": "entity", "fill": "#1B9E77"}}],
  "edges": [{"id": "a.Entity|entity_relation|owner", "source": "a.Entity", "target": "b.Entity", "data": {"label": "Association", "edge_type": "entity_relation"}}]
}
```

`id` equals the graph document's edge id, computed for a `1.0` graph. No new endpoint: Diff reads this one for each version, with `/api/v1/compare` beside them (spec 038). Keys and logs follow spec 037.
