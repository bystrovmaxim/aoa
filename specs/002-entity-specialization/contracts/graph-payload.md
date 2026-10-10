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
  "field_id": "events.model.EventEntity:details",
  "name": "details (by event_type)",
  "type": "CreatedEvent (created_event) | UpdatedEvent (updated_event) | DeletedEvent (deleted_event)",
  "primary_key": false,
  "foreign_key": true
}
```

**Why the pair and not one of the two.** The code is what the column **holds** — it is the value in the row — and the class is what that value **becomes** when the row is loaded. A reader of the diagram is usually asking one of two questions, "what can be in this column" and "where does each value live", and showing only the codes answers the first while leaving the second to be guessed, while showing only the classes answers the second and hides the actual data. Both, code in brackets after the class, is the only form that answers either question without a lookup.

**Why the `Entity` suffix is dropped.** Every entity in the diagram carries it, so it distinguishes nothing and costs width in the narrowest part of the table. The suffix is removed for display only: the payload's identifiers stay qualified names, and nothing that resolves a class reads this string.

An edge carries `labels` beside `alternatives`: the same list, same order, spelled for a reader — `<Class> (<code>)` with the shared `Entity` suffix dropped — while `alternatives` keeps the qualified name that resolves a class. The ERD reads `labels` instead of parsing `alternatives`, so the display form is decided in one place, where the class is in hand, rather than by a string operation in SQL.

**What is still not in this row, and why.** The classifier appears in `name` and not in `type`, because it is not a type — it is the field that picks among them. `foreign_key` stays `true`: the column does point outside the table, and the ERD's own colouring keys off that flag, so a specialization field that set it to `false` would be drawn as an ordinary scalar and the axis would disappear from the picture entirely.

There are **no** per-alternative `FK -> X` field rows: the union row is the whole point, because N foreign-key rows say N independent links where the model says one link to one of N tables (FR-024).

The payload gains a **group** per axis, and the client draws the alternatives inside it:

```json
{
  "group_id": "events.model.EventEntity:details",
  "label": "details (by event_type)",
  "members": ["events.model.CreatedEventEntity", "events.model.UpdatedEventEntity", "events.model.DeletedEventEntity"],
  "classifier_field": "event_type"
}
```

A group is **a drawing, not a table**. Its members keep their own nodes, columns and relations to the outside world (FR-027), so a consumer that ignores groups sees exactly the diagram it sees today.

**A group is ERD-only, and this payload is the only place it exists** (FR-030). The full-graph payload has no notion of one — checked, not assumed: the word does not occur in `full_graph_action.py` at all — and neither do the use-case and lifecycle builders, which read their own vertex kinds. So the grouping cannot leak into another drawing by construction, and no other drawing needs a flag to switch it off. The `entity_specialization` **edges** do reach the full graph, as ordinary associations, and that is intended: the system view shows that a link exists, while the ERD shows how a reader should compare the tables it leads to. The group is emitted only when the axis has more than one alternative: a single alternative is a plain relation, and a box around one table would claim a choice that does not exist (FR-028).

The `relations` list gains **one entry per axis**, not per alternative — one line into the container, labelled with the classifier (FR-029):

```json
{
  "source": "events.model.EventEntity",
  "target": "events.model.EventEntity:details",
  "label": "by event_type",
  "relationship_kind": "specialization",
  "source_cardinality": "zero_many",
  "target_cardinality": "one"
}
```

The generalization relations — extension to head, one per alternative — stay a **model** fact and are carried by the graph edges, not by this payload: the diagram draws the axis, and the graph knows every direction.

## Rendering


The Graphviz builder draws relation lines with no arrowhead attribute today, which means Graphviz's default filled arrow for every relation alike. Two notations are needed now, and both are taken from the use-case builder in the same client rather than invented:

  - the axis line, head to container, uses `arrowhead=vee` — the association style that builder already uses for a plain link;
  - the generalization line, extension to head, uses `arrowhead=empty style=solid penwidth=1` — the hollow triangle that builder already uses for an inheritance link.

The hollow triangle points at the **head**: the notation reads "this table is a variant of that one", and drawing it the other way would say the head inherits from each variant.

The group becomes a Graphviz **cluster** — `subgraph cluster_<id>` — with the label on the boundary, which is the mechanism the use-case builder in the same client already uses for its system boundary. A cluster in Graphviz is a drawing instruction: the nodes inside it are declared inside the `subgraph` and referenced by the same ids from outside, so the edges are unaffected and a member table can be pointed at from anywhere.

A member table is **declared inside the cluster and nowhere else**. Graphviz gives a node to the first subgraph that declares it, so declaring a member both inside and outside would silently drop it from the container — and the diagram would show the grouping for some members only.
