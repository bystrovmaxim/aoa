# Contract: `Entity` node kind properties in `graph-json`

Owner: `aoa-action-machine`, `graph/graph_json_schema.py`.

```json
"entity_kind": {
  "type": "string",
  "minLength": 1,
  "pattern": "^[a-z][a-z0-9_]*$",
  "description": "The kind word of the kind base class the entity inherits, taken from that class's name: BaseCoreEntity -> core. AOA's own model declares six; the value is open so that a graph from any producer can state a kind this engine does not know. AOA checks the declaration of a kind at class creation, not here."
},
"entity_kind_label": {
  "type": "string",
  "minLength": 1,
  "description": "The display name the kind base class declares for its kind: BaseAssocEntity -> Association. Optional on the wire, so that a producer with no names stays valid; AOA always writes it."
}
```

- `entity_kind` stays in `required`; `entity_kind_label` does not enter it.
- The branch "`entity_kind` = `enum` ⇒ `values` required" is unchanged.

| Row | Result |
|---|---|
| `entity_kind: "aggregate"` with or without `entity_kind_label` | valid |
| `entity_kind` missing, `""`, `"Core"`, `"core entity"`, `1` | invalid |
| `entity_kind_label: ""` or non-string | invalid |

AOA export example (`PlayerCoreEntity`):

```json
{"entity_kind": "core", "entity_kind_label": "Core", "description": "…"}
```
