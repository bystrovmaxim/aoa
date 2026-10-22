# Contract — the kind on the wire and in the store

**Feature**: `specs/013-entity-type-markers` | **Audience**: whoever produces or reads the interchange graph JSON and the Maxitor store.

## The row

An entity row produced by `NodeGraphCoordinator.build()` gains one property:

```json
{
  "id": "aoa.demo.model.store.entities.sales_core.SalesOrderCoreEntity",
  "type": "Entity",
  "label": "SalesOrderCoreEntity",
  "properties": {
    "description": "Customer order",
    "entity_kind": "core"
  }
}
```

| Key | Rule |
| --- | --- |
| `entity_kind` | required on every `Entity` row; one of `core`, `assoc`, `detail`, `spec`, `enum`, `state` |
| where it comes from | the kind base class in the class's chain: its name without `Base` and without `Entity`, lower case |
| the set of properties | unchanged otherwise: `additionalProperties` stays `false`, so no other key is admitted and no key is optional |
| `id`, `label` | unchanged rules — qualified class name and class `__name__`; the renames change the values, not the rules |

**Validation**: `GRAPH_JSON_SCHEMA` (`packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`) requires the key. A row without it is rejected — that is the test that proves the schema is not merely tolerant.

## Values

| Word | Kind base class it comes from |
| --- | --- |
| `core` | `BaseCoreEntity` |
| `assoc` | `BaseAssocEntity` |
| `detail` | `BaseDetailEntity` |
| `spec` | `BaseSpecEntity` |
| `enum` | `BaseEnumEntity` |
| `state` | `BaseStateEntity` — never produced: status types are excluded from the model graph |

The value is not stored on the class and not looked up in a table: it is the kind base class's own name, transformed once. Rename the base class and the suffix and the word move together, so they cannot disagree.

## The Maxitor store

| Site | Change |
| --- | --- |
| `entity` table DDL (`duckdb_graph_resource.py`) | `entity_kind VARCHAR NOT NULL` |
| `_fill_table_entity` | inserts `row["properties"]["entity_kind"]` |
| node payload builder for `entity` | adds `'entity_kind', entity_kind` to the rebuilt JSON |

A row with no kind fails the schema before the store sees it, so the insert has no absent-value path and the column needs no default. Because the store is rebuilt from graph JSON on every load, there is no migration of a stored file and no compatibility window.

## What does not change

- The number of entity rows, field rows, relation edges and lifecycle edges — the kind is a property, not a node.
- The `label` of a row: a rename changes it, the feature does not.
- Any drawing: the client does not read `entity_kind` in this change, so the diagrams render exactly as they do today, with the new class names.
- Any other row type: `Action`, `EntityField`, `State`, `Resource`, `Domain` and the edges keep their payloads.

## What a reader may rely on

- The kind of a row is the kind of the base class of the class it came from, and the two are checked against each other in a test.
- A row's kind survives the store: what `build()` emits is what the store returns.
- The six words are a closed set; a seventh would be a defect, not an extension.
