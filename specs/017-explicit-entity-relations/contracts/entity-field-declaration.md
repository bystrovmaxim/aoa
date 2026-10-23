# Contract: a field whose type is an entity is declared explicitly

**Feature**: `specs/017-explicit-entity-relations` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

A model author writes one line. This contract fixes what that line may say when its type is another entity, what the framework answers when it says neither legal thing, and where the answer is produced.

## 1. The two legal forms

```python
# form 1 — the field is a relation
showcase: Annotated[
    AssociationOne[ShowcaseCoreEntity],
    Inverse(ShowcaseCoreEntity, "players"),
] = Field(description="Player showcase, loaded from showcases")

# form 2 — the field is an embedded value, and the declaration says why
showcase: Annotated[
    ShowcaseCoreEntity,
    NoRelation("embedded showcase snapshot; no separate model relationship"),
] = Field(description="Showcase snapshot stored as a value")
```

| Rule | Statement |
| --- | --- |
| Form 1 | one of the eight relation containers: `AssociationOne`/`Many`, `CompositeOne`/`Many`, `AggregateOne`/`Many`, `Specialization`, `Generalization` |
| Form 2 | the exact entity type plus `NoRelation("reason")` inside `Annotated` |
| Optional | either form may be written with `\| None`; a bare `X \| None` is not a form |
| State entities | neither form applies: a `...StateEntity` type is described only by a `Lifecycle[...]` field |

## 2. What is refused

| Written | Answer |
| --- | --- |
| `showcase: ShowcaseCoreEntity` | refused: names the owner, the field, the resolved type and both forms |
| `showcase: ShowcaseCoreEntity \| None` | refused the same way |
| `items: list[ShowcaseCoreEntity]` | refused, naming the many-container forms |
| `items: dict[str, ShowcaseCoreEntity]`, `set[...]`, `tuple[...]` | refused the same way |
| `state: SomeStateEntity` | refused, naming the `Lifecycle[...]` form as the only one |
| `Annotated[SomeStateEntity, NoRelation("…")]` | refused, naming the `Lifecycle[...]` form |
| `Annotated[ShowcaseCoreEntity, NoRelation("")]` | refused at marker construction: the reason is blank |
| a container **and** `NoRelation` | refused: the two forms are mutually exclusive |

The refusal is one message per case, and every message has the same two parts: what is wrong with this field, and what to write instead.

```text
PlayerCoreEntity.showcase: the field's type is an entity (ShowcaseCoreEntity), so the field
cannot be a scalar. Declare it as a relation
(Annotated[AssociationOne[ShowcaseCoreEntity], Inverse(...)]) or as an embedded value
(Annotated[ShowcaseCoreEntity, NoRelation("why")]).
```

## 3. What is accepted unchanged

| Field | Why |
| --- | --- |
| `id: str`, `username: str`, `age: int \| None` | an ordinary scalar |
| `gender: GenderEnumEntity \| None` | a dictionary reference |
| `lifecycle: ClinicalSupplyLifecycle` | a lifecycle reference |
| `params: SomeParams` | a schema type, outside the ERD and outside this rule |

## 4. Where and when the rule runs

| Rule | Statement |
| --- | --- |
| Boundary | `NodeGraphCoordinator.build()`, in the pass that runs beside the specialization validation |
| Input | the resolved annotation from `model_fields` |
| Forward references | judged after resolution; a name that never resolves keeps its existing failure and is not reported as a scalar |
| Classes outside the graph | a class marked `exclude_graph_model` is skipped |
| Evaluating strings | never — no `eval`, no `get_type_hints` re-run, no inference from a field's name |
| Inherited fields | judged on the class that declares them, as `model_fields` reports them |

## 5. The embedded-value marker

| Rule | Statement |
| --- | --- |
| Meaning | this field stores the entity as a value; there is no model relation and no foreign key |
| Shape | frozen, stateless apart from the reason, value-equal, `__repr__` names the reason |
| Effect on the graph | none — the column stays a column and the reason does not travel to the graph, the payload or the card |
| Effect on validation | none — a nested value is still validated |
| Not `NoGraphEdge()` | `NoGraphEdge()` hides an edge of a relation that exists; `NoRelation` says no relation exists |
