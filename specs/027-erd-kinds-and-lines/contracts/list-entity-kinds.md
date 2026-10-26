# Contract: `GET /api/v1/list-entity-kinds`

Owner: `aoa-maxitor`, `ListEntityKindsAction` + `list_entity_kinds_action_schema.py`. Same source parameter, refusals (`400`, `422`, `503` with `Retry-After`) and headers as `GET /api/v1/list-domains`.

```
GET /api/v1/list-entity-kinds?source=<graph-json URL>
200
{"list_entity_kinds": [
  {"entity_kind": "assoc",  "label": "Association"},
  {"entity_kind": "core",   "label": "Core"},
  {"entity_kind": "detail", "label": "Detail"},
  {"entity_kind": "enum",   "label": "Enumeration"},
  {"entity_kind": "spec",   "label": "Specialization"}
]}
```

| Rule | |
|---|---|
| rows | one per distinct `entity_kind` among `entity` rows whose id is not `tests.%` and has no `<locals>` |
| order | `lower(entity_kind)` |
| `label` | always present: the smallest non-blank `entity_kind_label` of that kind, else the word with its first letter capitalised (`event` → `Event`, `unknown` → `Unknown`) |
| fields | exactly `entity_kind` (non-empty) and `label` (non-empty); `additionalProperties: false` |

Hand-built graph (`aggregate` labelled "Aggregate root", `event` and `link` unlabelled) → rows `aggregate`/Aggregate root, `event`/Event, `link`/Link.
