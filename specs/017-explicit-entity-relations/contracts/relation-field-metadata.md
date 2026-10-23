# Contract: a relation's description is metadata, never a runtime value

**Feature**: `specs/017-explicit-entity-relations` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

A relation field carries the value its caller supplies. Its documentation is metadata on the field. This contract fixes the default, the description, the two refusals, and what happens to a partially read entity.

## 1. The default contract

| Annotation and declaration | Omitted input (complete entity) | Explicit `None` |
| --- | --- | --- |
| `Relation[T] = Field(description=…)` | missing-field error | refused |
| `Relation[T] \| None = Field(description=…)` | missing-field error | accepted |
| `Relation[T] \| None = Field(default=None, description=…)` | `None` | accepted |
| `Relation[T] = Field(default=None, description=…)` | declaration refused | declaration refused |

`Relation[T]` stands for any of the eight containers. Nullability and optional input are separate choices: `| None` alone does not provide a default, and a default alone does not make a nullable field.

```python
# canonical required relation
customer: Annotated[
    AssociationOne[CustomerCoreEntity],
    Inverse(CustomerCoreEntity, "orders"),
] = Field(description="Customer who placed the order")

# canonical omittable nullable relation
main_resource: Annotated[
    AssociationOne[EnergyResourceCoreEntity] | None,
    NoInverse(),
] = Field(default=None, description="Primary resource; NULL when none is assigned")
```

## 2. What is refused at the declaration boundary

| Written | Answer |
| --- | --- |
| `= Rel(description=…)` | impossible: the symbol is gone, the module fails to import |
| any default other than an explicit `None` | refused: names the owner and the field |
| `= Field(default=None, …)` on a non-nullable relation | refused at declaration |
| `= Field(default_factory=…)` | refused, and the factory is never called |
| `= Field(description="")`, `= Field(description="   ")`, no description | refused |
| a prebuilt relation container as the default | refused |

## 3. The description

| Rule | Statement |
| --- | --- |
| Source | `FieldInfo.description` only |
| Both syntaxes | a `Field` inside `Annotated` and a `Field` in the assignment are merged by Pydantic into one `FieldInfo`; the assignment wins when both are present |
| Consumers | the relation intent resolver and the specialization intent resolver read the same attribute; the two fallback branches are deleted |
| Nonblank | a missing, empty or whitespace-only description is refused |
| Hidden edges | the rules hold when `NoGraphEdge()` hides the edge |

## 4. Partial reads

| Rule | Statement |
| --- | --- |
| Unaffected | a partial instance is built from any subset of non-key fields, without required-field checks |
| Access | reading a field the partial instance did not receive reports it as not loaded |
| Consequence | a declared requirement never forces a caller to read a whole entity or a whole graph |

## 5. The migration

| Rule | Statement |
| --- | --- |
| Scope | declarations, hydration callers, tests, docs and notebooks, in the phase that removes `Rel` |
| Nullable relations | each of the seven is decided by its full-construction call sites: `default=None` only where the field is omitted there, otherwise required but nullable |
| Unchanged | description text, relation targets, inverse matching, classifier mappings and edge semantics |
| Import | `Field` from `pydantic`; `Rel` no longer imported anywhere |
