# Phase 1 Data Model: Entity specialization

Three layers, each with its own shape: what the developer **declares**, what the build **holds** after parsing it, and what the wire **carries**. Everything below is inside `packages/aoa-action-machine` unless a line says otherwise.

## 1. Declaration vocabulary

### The head's field

```python
details: Annotated[
    Specialization[
        CreatedEventEntity | UpdatedEventEntity | DeletedEventEntity | MovedEventEntity | AssignedEventEntity,
    ],
    Classifier(
        field="event_type",
        codes=Literal["created_event", "updated_event", "deleted_event", "moved_event", "assigned_event"],
    ),
    Inverse(field_name="event"),
] = Rel(description="Event details: one of the declared extensions")
```

Four parts, each with one job:

| Part | Job |
| --- | --- |
| the **container** `Specialization[...]` | says which classes may be linked, and only those; its type argument is what pydantic enforces |
| `Classifier(field=…)` | names the classifier field whose value selects the alternative for a row |
| `Classifier(codes=Literal[…])` | names every declared code, in the order the alternatives are written |
| `Inverse(field_name=…)` | names the partner field every extension must declare |

### The extension's field

```python
event: Annotated[
    Generalization[EventEntity],
    Classifier("event", Literal["created_event"]),
    Inverse(EventEntity, "details"),
] = Rel(description="Event this extension belongs to")
```

The same container idea on the other side: `Generalization[...]` names the head, and the marker carries **this class's own code** — a `Literal` with exactly one member.

### The containers

| Container | Side | Members |
| --- | --- | --- |
| `Specialization[T]` | the head | `id`, `variant`, `entity` |
| `Generalization[T]` | the extension | `id`, `entity` |

Both are **pydantic models**, frozen, with `entity` excluded from `repr` — a head row and its extension can reference each other, and printing one would otherwise print the other forever. Subscripting either produces a real class, which is why a field of that type accepts an instance of it and refuses a bare entity, exactly as `AssociationOne[CustomerEntity]` behaves.

## 2. Build-time model

### Where the parser reads its input

| What | Where it lives | Note |
| --- | --- | --- |
| the alternatives | the container's type argument | pydantic stores it in `__pydantic_generic_metadata__["args"]`; `get_args` on the class returns nothing, because pydantic materialises a real class |
| the markers | `FieldInfo.metadata` | `Classifier`, `Inverse`, `NoGraphEdge`; `model_fields[field].annotation` is the container class, so metadata is the only place the markers appear |
| the codes | `Classifier.codes` (the `Literal`) and `Classifier.code_values` (plain strings, in order) | the build compares the whole set against what each extension declares |
| each extension's code | that class's own `Classifier` marker, reached through its reverse field | one member per class |

### `EntitySpecializationIntentResolver` — one axis, parsed

| Field | Type | Source |
| --- | --- | --- |
| `field_name` | `str` | the head field |
| `head_entity` | `type` | the class the field was read from |
| `classifier_field` | `str` | `Classifier(field=…)` |
| `alternatives` | `tuple[type, ...]` | the container's type argument, in declaration order |
| `codes` | `tuple[str, ...]` | `Classifier(codes=Literal[…])`, in declaration order |
| `description` | `str` | `Rel(description=…)` |
| `inverse_field` | `str` | `Inverse(field_name=…)` |
| `deprecated` | `bool` | `FieldInfo.deprecated`, as for the ownership relations |
| `omit_graph_edge` | `bool` | `NoGraphEdge()`, as for the ownership relations |

Derived once at parse time: `code_to_target`, the mapping a resource resolves a row's code against, and the graph publishes.

### The rules, and who checks them

**pydantic, when the class is defined or a value is assigned** — no framework code is involved:

| Rule | How it fails |
| --- | --- |
| a class outside the parameterised union | `ValidationError` when the value is assigned |
| another alternative under a narrower parameterisation | `ValidationError` on assignment |
| the containers are immutable | `ValidationError` on assignment to a member |

**the framework, when the model is built** — one global pass, `SpecializationDeclarationError` naming the class, the field and the rule:

| Rule | Scope |
| --- | --- |
| every class in the type argument is a declared `@entity`, so the graph has a node for it | axis |
| every class in the union declares exactly one code on its reverse declaration | global |
| the codes the head names equal the codes the classes declare — compared in **both** directions, with equal sizes | global |
| no code is declared twice within an axis, and a code names one class only | axis |
| every code is compatible with the classifier field's annotation | axis |
| mutuality: the classes reaching the head through a reverse declaration equal the classes in the union | global |
| closure: no class outside the union points at the field, and no extension carries a partner field for an axis the head does not declare | global |
| no class appears in the unions of two different heads | global |
| one head carries one field per classifier field | global |
| `Classifier(field=…)` names an existing scalar field of the head — not a relation, not a class constant, not a property — and not the specialization field itself | axis |
| the head and its extensions form no cycle | global |

**never a model invariant**, and therefore not checked: data completeness, data disjointness, and whether the codes present in the data match the declared ones.

## 3. Runtime value

### Three states

| State | What the field reads as |
| --- | --- |
| the row was loaded | `Specialization[...](id=…, variant=…, entity=<row>)` |
| only the link is known | `Specialization[...](id=…, variant=…)` — `.entity` is nothing, `id` and `variant` are readable |
| nothing was assigned | nothing |

The variant is stored rather than derived, because with an un-hydrated row the identifier says which row but not which of the N tables holds its continuation.

Consequences, all deliberate:

- **The field holds a container**, not a bare entity — the same shape the ownership relations use, so a link without a loaded row stays expressible.
- **No ownership flavour applies**, and no `isinstance` check against the ownership containers changes meaning: specialization is classification.
- **The process-mining walk does not visit it**: a specialized head row is one business object, and the extension it links to is part of that row's meaning.

## 4. Wire model

### The field stays one column

A specialization adds **no vertex**. The head's field keeps the `EntityField` row every
other field has, and that row is the single field entry the diagram shows. Two reasons,
both measured while building it: a vertex of its own would duplicate what the edges
already carry (the alternatives, their codes, the classifier), and its natural key —
``<head qualname>:<field name>`` — is exactly the column row's id, so the two could not
have coexisted anyway.

### Edge: `entity_specialization` (head → each alternative)

| Property | Type | Meaning |
| --- | --- | --- |
| `field_name` | `str` | the head's field — the cluster key a consumer groups by |
| `classifier_field` | `str` | the classifier field name |
| `classifier_value` | `str` | the code that selects **this** alternative |
| `alternative_index` | `int` | the position of this alternative in the declared order |
| `alternatives` | `list[str]` | the whole ordered list, repeated on every edge so a consumer reading one row has the set |
| `relation_type` | `str` | `"specialization"` — a value beside `composition` / `aggregation` / `association`, never mixed with them |
| `cardinality` | `str` | `"one"` — exactly one of the cluster applies to a row |
| `description` | `str` | the declared description |
| `has_inverse` | `bool` | `true` whenever the axis names a partner field; the one-way form does not exist (FR-013) |
| `deprecated` | `bool` | as declared |

### Edge: generalization (extension → head)

A `parent_*`-family generalization edge with `relationship = "Generalization"`, one per alternative, carrying `field_name` (the extension's partner field), `inverse_field` (the head's field), `classifier_value` (the code), and `head_entity_id`. It is excluded from the full-graph payload by the predicate that already excludes this relationship, and it reaches the ERD (see [research.md](./research.md), D4).

### ERD row (Maxitor payload, `list_entities_action`)

The head's `fields` list gains exactly one row where the extension set used to produce none:

| Field | Value |
| --- | --- |
| `name` | `<field> \| <code1> \| <code2> … (by <classifier>)` |
| `type` | the alternatives' labels, `" \| "`-joined |
| `primary_key` | `false` |
| `foreign_key` | `true` |
| `field_id` | the head field's own column row id, `<head qualname>:<field name>` |

The `relations` list gains one entry per alternative: `source` = head, `target` = the alternative's entity, `label` = the code, `relationship_kind` = `"specialization"`.

## 5. State

There is no state machine in this capability. The only lifecycle is a build order that matters:

```
import            markers defined; nothing validated yet
class definition  annotations and Rel(...) constructed; a bad marker argument fails here
graph build       parse each axis → run the build rules → wire edges and vertices
                  (NodeGraphCoordinator.build: after _single_pass_validate_and_wire,
                   before _validate_dag_acyclicity)
runtime           a resource reads a row, resolves its code against the declared mapping, and
                  assigns the extension object it built; a class outside the union is refused
```
