# Contract: a specialization axis takes its codes from a dictionary

**Feature**: `specs/015-closed-dictionary-variants` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md)

## 1. The declaration surface

```python
@entity(description="Edition kind", domain=ShopDomain)
class EditionKindEnumEntity(BaseEnumEntity):
    FIRST   = EditionKindEnumEntity(code="first",   display_name="First press")
    REPRESS = EditionKindEnumEntity(code="repress", display_name="Repress")


@entity(description="Record", domain=ShopDomain)
class RecordCoreEntity(BaseCoreEntity):
    id: str = Field(description="Record id")
    kind: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity, EditionKindEnumEntity],
        Inverse(field_name="record"),
    ] = Rel(description="Which pressing this is")


@entity(description="First-press data", domain=ShopDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(field="record", variant=EditionKindEnumEntity.FIRST),
    ] = Rel(description="The head row")
```

The dictionary is named **once**, as the second type argument of the head's specialization field. The head has **no classifier field** and **no `Classifier` marker**.

## 2. The container

```python
kind = Specialization[id]  # id: Any, variant: D, entity: T | None
```

| Aspect | Rule |
| --- | --- |
| `variant` input | a declared value, or its reference object `{code, display_name, properties}` |
| `variant` refused input | a bare code string; a constructed copy; a value of another dictionary |
| held value | the declared instance, by identity |
| `entity` | the hydrated extension row, or `None` when the row was not loaded |
| pairing | when `entity` is not `None`, `type(entity).declared_variant` must be the same object as `variant` |
| absent variant | the head field is `None`; the container is not built |
| serialization | `{"code", "display_name", "properties": {…extra declared fields…}}` |
| read rule | `code` is authoritative; the other fields are cargo and are not compared |

`declared_variant` is derived on every `BaseSpecEntity` descendant from its own `Generalization[…]` + `Classifier(variant=…)` declaration; it is not written by hand and it is not a second source of truth.

## 3. The storage read path

Storage keeps a column holding the code. Its name is **not fixed** and is chosen by the resource; the model never sees it. The resource:

1. reads the column and the row id;
2. resolves the code with `by_code`, wrapping `KeyError` into a domain error naming the row id, the field, the code and the declared set;
3. picks the extension class whose declaration carries that code;
4. passes the declare value and the hydrated row into the container.

```python
try:
    value = EditionKindEnumEntity.by_code(row["edition_key"])
except KeyError:
    raise UndeclaredValueError(
        f"record {row['id']!r}: kind={row['edition_key']!r} is not a declared value of "
        f"EditionKindEnumEntity. Declared: {EditionKindEnumEntity.codes()}."
    ) from None

kind = RecordVariant(id=ext_id, variant=value, entity=ext_cls.partial(note=ext_note))
record = build(row, RecordCoreEntity, lambda e, r: {e.id: r["id"], e.kind: kind})
```

A head row with no variant leaves the field `None`; a variant whose extension row was not loaded keeps the value and `entity=None`.

## 4. The graph surface

Each alternative produces one `entity_specialization` edge from the head's field to the alternative's class, and each extension produces one `parent_entity` edge back to the head. Axis edges carry:

```json
{"relationship": "specialization",
 "properties": {"field_name": "kind",
                "classifier_value": "first",
                "dictionary_qualname": "shop.model.EditionKindEnumEntity",
                "dictionary_label": "Edition kind"}}
```

- `classifier_field` is **not** carried: the head has no classifier field.
- The alternatives appear in the dictionary's declaration order, because a union has no order of its own.
- The head's card loses the selector column; the container label in the viewer reads `kind (by Edition kind)`.

## 5. Refusals and their messages

| Case | Message names |
| --- | --- |
| a head keeps a `Classifier`, a separate classifier field, or `codes=Literal[…]` | the head, the field, and the single declaration form |
| the head field's second type argument is not a decorated, non-empty dictionary | the head, the field, the type |
| an extension's `field` is not a `Generalization[…]` field of that head | the extension and the field |
| an extension's `variant` is a code string, a foreign value or a copy | the extension, its field, the value to use |
| a declared value with no alternative | the axis field and the uncovered code |
| a container's value disagrees with the class of its `entity` | both values and the class |
| a bare code string reaches a dictionary-typed field | the field and the expected reference object |
| an undeclared code arrives from storage | the row id, the field, the code and the declared set (the resource's error) |

## 6. Guarantees kept from the previous design

1. The axis's code set is the dictionary's catalogue; it is not restated anywhere.
2. Every declared value has exactly one alternative; every alternative names a declared value.
3. The declared instance is used, not a copy; the message names the attribute.
4. One dictionary may classify several axes; each proves full coverage.
5. Every alternative is a declared entity; one class belongs to one head; no cycles. The classifier-field rules are gone with the field.
6. `Literal` is refused for specialization codes and stays for non-dictionary closed sets.
7. The checks run once per graph build, before the graph is published, and cost nothing at runtime.

## 7. Tests that assert this contract

- `packages/aoa-action-machine/tests/action_machine/domain/test_specialization_container.py` — the input shapes, the pairing check, `None`, serialization.
- `packages/aoa-action-machine/tests/action_machine/domain/test_spec_entity.py` — `declared_variant` derived, and refused when the marker is not a declared value.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_vocabulary.py` — the five build refusals, the shared dictionary, the edge properties.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_sweep.py` — the two-sided sweep, migrated.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py` and `…_rules_global.py` — the unchanged rules.

## 8. Migration

Every existing axis moves in the same commit as the rule: 1 in the demo, 48 in 38 example scripts with their 38 notebooks, 61 in 7 framework test modules. Each loses its classifier field, gains the dictionary argument, and its extensions gain `variant=`. The codemod derives one dictionary per axis from the existing `Literal`s; the negative examples that assert the replaced rules are rewritten by hand. No axis may keep a `Literal` for its codes after the change.
