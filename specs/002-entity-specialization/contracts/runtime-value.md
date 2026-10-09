# Contract: the runtime value

What a head's field holds, what it promises, and how it fails. The reader here is the developer writing a resource or a query, not the diagram.

## The value is a container

```python
pressing = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
    id="rec-1",
    variant="first",                 # which alternative this is
    entity=FirstPressEntity(id="rec-1", stamper="1A", year=1959),   # the row, when loaded
)

record = VinylRecordEntity(id="rec-1", title="Kind of Blue", media="first", pressing=pressing)

record.pressing.variant           # "first" — which table holds the continuation
record.pressing.entity            # FirstPressEntity(...)
record.pressing.entity.stamper    # "1A"
```

The container is the same shape the ownership relations use: a field of type `AssociationOne[CustomerEntity]` also holds a container, not the entity. Here the container additionally carries **which variant** it is, because the identifier alone says which row but not which of the N tables holds it.

## Three states

| State | What the field reads as |
| --- | --- |
| the row was loaded | `Specialization[...](id=…, variant=…, entity=<row>)` — `.entity` is the row |
| only the link is known | `Specialization[...](id=…, variant=…)` — `.entity` is nothing, and the id and variant are still there |
| nothing was assigned | nothing |

The middle state is why the variant is stored: with an un-hydrated row there is otherwise no way to tell which table to go to.

## The declaration states the codes, and the model checks both sides

```python
# the head: which classes may be linked, which field chooses, which codes exist
pressing: Annotated[
    Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
    Classifier(field="media", codes=Literal["first", "repress", "test"]),
    Inverse(FirstPressEntity, "record"),
] = Rel(description="How this record was pressed")


# every extension: the way back, and its own code
@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")
```

Three declarations name the same set, and the build compares them in both directions:

| What | Where it is written |
| --- | --- |
| the classes | the type argument of `Specialization[...]` |
| the codes | the `Literal` in the head's `Classifier` |
| which code belongs to which class | each extension's own `Classifier`, one member |

The checks: every class in the union declares exactly one code; the set of those codes equals the set named by the head's `Literal`; the counts agree; and a class named by no extension, or a code no class declares, fails the build naming what is missing. Order pairs a class with a code for reading, but the check itself is by membership, so reordering the two lists alone never breaks a model.

The code is therefore written twice on purpose — once as the vocabulary the head names, once beside the class it selects — and that duplication is exactly what the build compares. Neither copy is the authority; the match is.

## The two containers

| Container | Side | Members |
| --- | --- | --- |
| `Specialization[T]` | the head | `id`, `variant`, `entity` |
| `Generalization[T]` | the extension | `id`, `entity` |

Both are frozen pydantic models, so subscripting one produces a real class: a narrower subscription (`Specialization[FirstPressEntity]`) refuses another alternative, and a class outside the union is refused on assignment. `entity` is excluded from `repr`, because a head row and its extension can reference each other and printing one would print the other forever.

Neither inherits the ownership containers: specialization is classification, not ownership, so an `isinstance` check against composition, aggregation or association keeps meaning what it meant.

## What a resource does with the mapping

Reading a row whose code is not declared is an explicit failure naming the value, never "no relation": a missing continuation and an undeclared one are different facts about the data. The mapping the resource resolves against is published by the graph, and resolving is the resource's own explicit step — the framework matches nothing behind the developer's back.
