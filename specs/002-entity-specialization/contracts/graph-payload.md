# Contract: the graph payload and the ERD

What the interchange carries for a specialization, and what the diagram makes of it. The schema in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py` is checked in and enforced by tests, so every shape below has a `$defs` entry and a `link.oneOf` branch.

## The field stays one column

A specialization adds **no vertex**. The head's field keeps the `EntityField` row every
other field has, and that row is the single field entry the diagram shows:

```json
{
  "id": "events.model.EventEntity:details",
  "type": "EntityField",
  "label": "details",
  "properties": {
    "field_type": "Specialization[CreatedEventEntity | UpdatedEventEntity]",
    "primary_key_hint": false
  }
}
```

Three reasons it is this row and no other:

- **A reader has to see the field.** A head whose continuation lives in another table
  must show the field it continues through; N edges without the column would hide it.
- **A second vertex would duplicate the edges.** The alternatives, their codes and the
  classifier already travel on every edge, and a vertex carrying them again would be a
  second copy of one fact — the thing this design keeps removing.
- **A vertex of its own would collide.** Its natural key is
  ``<head qualname>:<field name>``, which is exactly the column row's id, and the
  coordinator keys nodes by id alone.

**What is not yet right here**: `field_type` currently carries the Python name of the
container — ``Specialization[Union[CreatedEventEntity, UpdatedEventEntity]]`` — which is
neither a data type nor readable in a diagram. The ERD work in this phase turns it into
the readable list of alternatives, and that is where the row's `name` and `type` are
decided.

## Edge: `entity_specialization` (head → each alternative)

One edge per alternative, so a consumer that walks edges reaches every target a foreign-key walk would look for. Every edge repeats the whole ordered alternative list, so a single row is enough to reconstruct the declaration.

```json
{
  "source_id": "events.model.EventEntity",
  "target_id": "events.model.CreatedEventEntity",
  "type": "entity_specialization",
  "relationship": "Association",
  "is_dag": false,
  "properties": {
    "field_name": "details",
    "classifier_field": "event_type",
    "classifier_value": "created_event",
    "alternatives": [
      "created_event -> events.model.CreatedEventEntity",
      "updated_event -> events.model.UpdatedEventEntity"
    ],
    "relation_type": "specialization",
    "cardinality": "one",
    "description": "Event details: one of the declared extensions",
    "has_inverse": true,
    "deprecated": false
  }
}
```

- `relation_type` is `"specialization"` — a value **beside** `composition` / `aggregation` / `association`, never a fourth ownership flavour (`RelationType` is unchanged).
- `cardinality` is `"one"`: a head row points at exactly one alternative.
- Two names, kept apart: `classifier_field` is the field of the head whose value chooses, and `classifier_value` is the code this one alternative is chosen by. The vertex carries the field name only, because one axis has one classifier field; the edge carries the field name **and** the code, because an edge denotes exactly one alternative.
- `alternatives` is the declaration order, and a consumer must not sort it: the ERD row's order is the developer's order.
- **The edges of one axis are a cluster, and that is what makes them alternatives rather than N independent links.** The key is `field_name` — the same property the ownership relations already carry their field name in — and `relation_type` says what kind of cluster it is. So a consumer groups by `field_name` and reads the rule: **exactly one of these edges applies to a row**, and `classifier_field` names the value that decides which. The set is closed: the build refuses a class that points at the axis without being named in it, so every edge carrying the same `field_name` belongs to the whole declaration.
- The closedness is a guarantee of the build, not a property written on the edge. A consumer that knows `relation_type` knows the grouping rule; one that does not sees edges that are shaped exactly like ordinary relations, which is deliberate — there is no second shape to learn.
- The edge is `is_dag = false`, like the other entity relations, because an entity graph may contain cycles.

## Edge: generalization (extension → head)

```json
{
  "source_id": "events.model.CreatedEventEntity",
  "target_id": "events.model.EventEntity",
  "type": "parent_entity",
  "relationship": "Generalization",
  "is_dag": false,
  "properties": {
    "field_name": "event",
    "inverse_field": "details",
    "classifier_value": "created_event",
    "head_entity_id": "events.model.EventEntity"
  }
}
```

- The direction is extension → head, because that is the direction the relation reads as generalization.
- `classifier_value` is what makes the reverse edge carry the same fact as the forward one, so an ERD that draws only these edges can still label them with the code.
- **The full-graph payload keeps excluding this relationship** through the predicate that already excludes it (`relationship <> 'Generalization'` in `full_graph_action.py`). That is intended, it is stated in a test, and the edges remain in DuckDB where the ERD reads them.

## ERD payload (Maxitor, `list-entities`)

The head's `fields` list gains exactly **one** row:

```json
{
  "field_id": "events.model.EventEntity.details",
  "name": "details | created_event | updated_event | deleted_event (by event_type)",
  "type": "CreatedEvent | UpdatedEvent | DeletedEvent",
  "primary_key": false,
  "foreign_key": true
}
```

and the `relations` list gains **one entry per alternative**:

```json
{
  "source": "events.model.EventEntity",
  "target": "events.model.CreatedEventEntity",
  "label": "created_event",
  "relationship_kind": "specialization",
  "source_cardinality": "zero_many",
  "target_cardinality": "one"
}
```

There are **no** per-alternative `FK -> X` field rows: the union row is the whole point, because N foreign-key rows say N independent links where the model says one link to one of N tables (FR-024).

## Rendering

The Graphviz builder emits an explicit arrowhead for these relations (`arrowhead=onormal`, the hollow triangle at the head end), because the notation has to say "is a variant of" and the default filled arrow says the opposite. Today the ERD draws no relation notation at all, so this is the first — the use-case diagram is the precedent, not the ERD.
