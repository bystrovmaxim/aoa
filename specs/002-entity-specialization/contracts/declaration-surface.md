# Contract: the declaration surface

What a developer writes to declare a specialization, and what the build promises in return. Everything here is declaration-time or build-time behaviour of the engine; nothing here is storage, transport or diagram.

## Declaring one head field with N alternatives

```python
@entity(description="Event", domain=EventsDomain)
class EventEntity(BaseEntity):
    id: str = Field(description="Event id")
    event_date: date = Field(description="When the event happened")
    event_type: str = Field(description="Classifier: which extension table holds the details")

    details: Annotated[
        Specialization[CreatedEventEntity | UpdatedEventEntity | DeletedEventEntity],
        Classifier(field="event_type", codes=Literal["created_event", "updated_event", "deleted_event"]),
        Inverse(field_name="event"),
    ] = Field(default=None, description="Event details: one of the declared extensions")
```

- The field's **type parameterises a container with the alternatives**: `Specialization[A | B | C]`, which is where the "one of these, and only these" rule is enforced — pydantic refuses a class the union does not name, and a narrower parameterisation refuses the other alternatives (FR-001, FR-028). A consequence to expect: a field of this shape is a relation for every consumer, so each place that decides "is this a relation?" needs an explicit branch for it — a place that keeps asking its old question silently drops the relation, which is the failure this capability exists to remove.
- `Classifier(field=…)` is **mandatory** and names a scalar field of the same entity; its `codes` is a `Literal` naming every declared code, in the order the alternatives are written. Without it neither the runtime knows which table to go to nor can a storage consumer tie a code to a table (FR-010, FR-011).
- `Inverse(field_name=…)` on the head names **only the partner field name**: the entities are already listed in the `Specialization` markers, and this is why every alternative must name its partner field the same way (FR-012).
- The head field's value is `Field(default=None, description=…)`, **not** `Rel(…)`: what the field holds is an extension object, so `Rel` — which marks a field whose value is a relation — belongs to the extension side. A head field left unset reads as nothing; a field declared with a `Rel` default would read as that marker instead, which is not a value of this field at all.
- At **least one** class in the union; a union is never empty, so the degenerate case is a field that names no alternative at all and is therefore not a specialization field (FR-002).
- The classifier is a marker **object**, not a keyword: `Annotated[int, Classifier(...)]` parses, while a bare `by="event_type"` inside the brackets is a `SyntaxError`. This is why the declaration reads `Classifier(...)` beside `Inverse(...)`.
- The value put into the field is the container: `Specialization[...](id=…, variant=…, entity=<row>)`. The row is refused when its class is not in the union, and the identifier and the variant stay readable when no row was loaded (FR-026, FR-028).

## Declaring the reverse side

```python
@entity(description="Event created", domain=EventsDomain)
class CreatedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the Event row")

    event: Annotated[
        Generalization[EventEntity],
        Classifier("event", Literal["created_event"]),
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")
```

- The reverse side is **mandatory**: `NoInverse()` on either side is an error, because a specialization without a reverse side does not exist (FR-013).
- The **code is declared twice, on purpose** — once beside the alternative on the head and once beside the partner field on the extension — and the build compares them. Neither side is the authority; the match is (FR-014). A mismatch fails the build naming both codes and both sides.
- `Generalization`'s target must be **exactly the head**: not an ancestor of it, not a protocol (FR-017).
- An extension is an ordinary entity otherwise: its own fields, its own relations, its own lifecycle, and it may itself be the head of another specialization (FR-021).

## Several axes over the same extensions

A head may carry **more than one** axis — one field per classifier — and every axis names the same set of extension classes:

```python
    details: Annotated[
        Specialization[CreatedEventEntity | UpdatedEventEntity],
        Classifier(field="event_type", codes=Literal["created_event", "updated_event"]),
        Inverse(field_name="event"),
    ] = Rel(description="Which extension table holds the details")

    origin: Annotated[
        Specialization[CreatedEventEntity | UpdatedEventEntity],
        Classifier(field="channel", codes=Literal["web", "mobile"]),
        Inverse(field_name="origin_event"),
    ] = Rel(description="Where the event came from")
```

Each extension then declares **one partner field per axis**, and each axis's codes are its own vocabulary — the same extension declares `created_event` on one axis's reverse field and `web` on the other's (FR-009, FR-012, FR-019). Every axis of one head names the same set of classes, because an extension has exactly one head.

## What the build refuses

Every refusal is a `SpecializationDeclarationError` naming the class, the field and the rule; it is raised while the graph is assembled, never on a call and never silently.

| The declaration | Rule |
| --- | --- |
| a field with no `Specialization` entries | FR-002 |
| an alternative that is not an `@entity` class | FR-003 |
| the same class twice in one list | FR-004 |
| the same code twice in one axis, or an empty code | FR-005 |
| a code the classifier's type cannot hold | FR-006 |
| one alternative a subclass of another, or of the head | FR-007 |
| a class listed by two different heads | FR-008 |
| two axes of one head with different class sets | FR-009 |
| no `Classifier` | FR-010 |
| `Classifier(field=…)` naming a relation, a class-level constant, a property, a missing field, or the specialization field itself | FR-011 |
| an alternative with no partner field | FR-012 |
| `NoInverse()` on either side | FR-013 |
| the extension's code differing from the head's | FR-014 |
| a class pointing at an axis whose list does not contain it, or at an axis the head does not declare | FR-016 |
| a partner field whose target is an ancestor of the head, or a protocol | FR-017 |
| a head→extension cycle, including a class that is its own ancestor through a chain | FR-018 |

## What is not a rule, deliberately

- **Data completeness** — that every head row has an extension row. The relation is optional and no declaration states otherwise.
- **Data disjointness** — that a row lives in one extension table. For a single-valued field this already follows from the field's cardinality.
- **The data's codes matching the declared ones** — only a storage-level check can enforce it. The engine publishes the mapping so a consumer can; it does not generate the constraint.
