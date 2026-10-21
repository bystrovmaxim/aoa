# Contract — the state row, the diagram store and the FSM snapshot

**Feature**: `specs/012-lifecycle-state-vocabularies` | **Date**: 2026-10-19

Three layers read a status after the chain has accepted it: the interchange graph, the DuckDB store Maxitor loads, and the FSM snapshot the browser draws. This contract fixes what each carries.

## 1. Graph state row

**Before**

```json
{
  "id": "aoa.demo.model.store.SalesOrderEntity:lifecycle:lifecycle:payment_pending",
  "type": "StateIntermediate",
  "label": "payment_pending",
  "properties": {
    "lifecycle_class_id": "aoa.demo.model.store.SalesOrderLifecycle",
    "state_key": "payment_pending"
  }
}
```

**After**

```json
{
  "id": "aoa.demo.model.store.SalesOrderEntity:lifecycle:lifecycle:payment_pending",
  "type": "StateIntermediate",
  "label": "Payment pending",
  "properties": {
    "lifecycle_class_id": "aoa.demo.model.store.SalesOrderLifecycle",
    "state_key": "payment_pending",
    "attributes": {
      "code": "payment_pending",
      "display_name": "Payment pending",
      "sort_order": 2,
      "color": "#1565c0"
    }
  }
}
```

**Unchanged**: `id`, `type`, `properties.lifecycle_class_id`, `properties.state_key`, every transition edge (`<state id>` → `<state id>`, properties `from_state` / `to_state`), the `lifecycle_contains_state` edges.

**Changed**: `label` is the display name; `properties.attributes` exists.

**Graph JSON schema**, `$defs.state.properties`:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["lifecycle_class_id", "state_key"],
  "properties": {
    "lifecycle_class_id": {"type": "string"},
    "state_key": {"type": "string"},
    "attributes": {"type": "object"}
  }
}
```

The envelope stays strict; the inside of `attributes` is free, so a new domain field needs no schema change.

**Compatibility**: a row without `attributes` stays valid (it is not required); the store reads it as an empty object. During phases 1–4 a state declared with the string form keeps its key as the label and carries `{}` as attributes. A status field that cannot be represented as JSON fails the build — the row is never emitted broken.

## 2. DuckDB `state` table

**Before**

```sql
CREATE TABLE state (
    id VARCHAR PRIMARY KEY,
    label VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    lifecycle_class_id VARCHAR NOT NULL,
    state_key VARCHAR NOT NULL
);
```

**After** — one column added:

```sql
attributes JSON
```

**Nodes view** — `attributes` exposed in the payload:

```sql
SELECT id, label, kind AS type,
       json_object('lifecycle_class_id', lifecycle_class_id,
                   'state_key', state_key,
                   'attributes', attributes) AS payload
FROM state
```

**Unchanged**: every other table and view, the `lifecycle` and `state_edges` queries, the load endpoint, the full-graph query. A graph JSON without attributes loads and yields `{}`.

## 3. FSM snapshot

**State item**

```json
{
  "key": "payment_pending",
  "display_name": "Payment pending",
  "state_type": "intermediate",
  "transitions": ["cancelled", "confirmed"],
  "attributes": {"code": "payment_pending", "display_name": "Payment pending", "sort_order": 2, "color": "#1565c0"}
}
```

**Schema**: `attributes` is a **closed** object on the state item — `code`, `display_name`, `sort_order`, `color`, `fill_color`, `additionalProperties: false`; `key`, `display_name`, `state_type`, `transitions` stay required; no field is removed. The strict wire-schema type refuses a free-form object, so this is the diagram contract: arbitrary domain fields remain in the graph state row and are dropped here.

**Order**: initial first, then `attributes.sort_order` (default `0`), then `key`. With no `sort_order` anywhere, the order equals today's (`initial` first, then key).

**Compatibility**: a client that ignores `attributes` keeps working; the four existing fields are unchanged, except that `display_name` is now the human label instead of the key — which is the defect this feature fixes.

## 4. Diagram source (DOT)

For every state node:

| Input | Stroke | Fill |
| --- | --- | --- |
| `attributes.color` present | that colour | per-type palette |
| `attributes.fill_color` present | `attributes.color` if present, otherwise the palette | that colour |
| no attributes | per-type palette | per-type palette |

With no attributes anywhere, the generated DOT is byte-identical to today's.
