# Diagnosing a specialization declaration

Use this guide when a model that declares variant-specific details is refused, or when you need to check exactly what a declaration rule means. The examples use a record catalogue: `VinylRecordCoreEntity` holds common information, and three pressing classes hold different kinds of details. The common class is the **head** and the pressing classes are its **alternatives**. If these terms are new, first read the [relations tutorial](../tutorials/step-21-relations.md#generalization-and-specialization).

A head names a **closed dictionary** as the second type argument of its container, and each alternative names one of that dictionary's **values** in its own `Classifier` marker:

```python
@entity(description="Kind", domain=MusicDomain)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    EARLY = VinylRecordKindEnumEntity(code="early", display_name="Early")
    REPRESS = VinylRecordKindEnumEntity(code="repress", display_name="Repress")


class VinylRecordCoreEntity(BaseCoreEntity):
    id: str
    title: str
    pressing: Specialization[FirstPressSpecEntity | RepressSpecEntity, VinylRecordKindEnumEntity] = Rel(...)


class FirstPressSpecEntity(BaseSpecEntity):
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(field="record", variant=VinylRecordKindEnumEntity.EARLY),
    ] = Rel(...)
```

Two consequences are worth knowing before reading the refusals. A head has **no classifier field** any more: the dictionary is the closed set of values, and the value lives on the row that names it. And a code is not a value: the resource resolves a stored code before the model sees it, so `variant="early"` is refused while `variant=VinylRecordKindEnumEntity.EARLY` is accepted.

Each experiment below changes one aspect of a working declaration. Its script and notebook contain the complete model, the diagnostic call and the printed answer. Run the programs separately: AOA discovers loaded entity declarations, so importing an intentionally broken example into another experiment would change what that experiment validates.

## The refusals, at a glance

| What is wrong | The report says | Experiment |
|---|---|---|
| The head names no dictionary | `is a specialization container whose second type argument is not a closed dictionary` | `20_error_missing_classifier` |
| The dictionary declares nothing | `declares no values` | `test_entity_specialization_vocabulary` |
| An alternative names no value | `names no value of '…'` | `21_error_missing_code` |
| A borrowed value has no alternative | `code(s) ['…'] are named by the head but no alternative declares them` | `23_error_unknown_head_code` |
| Two alternatives name one value | `the head names 2 code(s) for 3 alternative(s)` | `25_error_duplicate_code` |
| An alternative is not an entity | `is not a declared entity` | `32_error_undeclared_entity` |
| The reverse field is named differently | `but the axis names` | `29_error_inverse_name` |
| An alternative points back through two fields | `more than one field` | `31_error_two_reverse_fields` |
| An alternative has no reverse field | `no alternative declares them` | `30_error_no_reverse` |
| Two heads claim one alternative | `is an alternative of` | `34_error_two_heads` |
| A class points at the axis without being named | `without being named` | `35_error_outside_alternative` |
| A value belongs to another dictionary | `does not declare` | `test_entity_specialization_vocabulary` |
| The value disagrees with the loaded row | `does not match` | `08_specialization_mismatched_data` |
| A stored code arrives bare | `a bare code is not accepted` | `07_specialization_data_codes` |
| The marker is given a code list | `must be a declared dictionary value` | `41_error_codes_not_literal` |

## The head names no dictionary

What it looks like: the container carries one type argument, or a second one that is not a dictionary, such as `Specialization[FirstPressSpecEntity | RepressSpecEntity, str]`.

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid:
is a specialization container whose second type argument is not a closed dictionary;
write Specialization[Alternatives, Dictionary]
```

A one-argument container does not even get that far: `Specialization[A | B]` is a `TypeError` at class creation, because the dictionary is part of the type.

**Repair**: declare the dictionary and name it in the container. See `examples/step_21_relations/20_error_missing_classifier.py`.

## An alternative names no value

What it looks like: the reverse field carries no `Classifier`, or one that still holds a list of codes.

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid:
alternative 'FirstPressSpecEntity' names no value of 'VinylRecordKindEnumEntity' —
write Classifier(field=..., variant=VinylRecordKindEnumEntity.<VALUE>)
```

**Repair**: name the value — `Classifier(field="record", variant=VinylRecordKindEnumEntity.EARLY)`. See `21_error_missing_code`.

## A borrowed value has no alternative

What it looks like: the head names a dictionary with a value that no alternative answers for, so the row that carries that value would have nowhere to go.

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid:
code(s) ['lost'] are named by the head but no alternative declares them
```

**Repair**: add the missing alternative, or remove the value from the dictionary. See `23_error_unknown_head_code`.

## Two alternatives name one value

What it looks like: two classes carry `variant=VinylRecordKindEnumEntity.EARLY`. The comparison is two-sided, so one of them is left with no value of its own.

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid:
the head names 2 code(s) for 3 alternative(s): every alternative needs exactly one code
```

**Repair**: give each class its own value. See `25_error_duplicate_code`.

## An alternative is not an entity

What it looks like: a class that is shaped like an alternative but was never decorated with `@entity`, so the graph would have no node for it.

```text
SpecializationDeclarationError: … alternative 'FirstPressSpecEntity' is not a declared entity — mark it with @entity
```

**Repair**: decorate the class. See `32_error_undeclared_entity`.

## The reverse field is named differently

What it looks like: the head's axis carries `Inverse(field_name="album")`, and the alternative points back through `record`.

```text
SpecializationDeclarationError: … alternative 'FirstPressSpecEntity' points back through 'record',
but the axis names 'album'
```

**Repair**: make the two names agree. See `29_error_inverse_name`.

## An alternative points back through two fields

What it looks like: two `Generalization` fields on one class point at the same head, so the axis cannot tell which one declares the value.

```text
SpecializationDeclarationError: … alternative 'FirstPressSpecEntity' points back through more than one
field (other_record, record); the axis cannot tell which one declares its code
```

**Repair**: keep one reverse field per head. See `31_error_two_reverse_fields`.

## An alternative has no reverse field

What it looks like: the class is named in the union but declares no field pointing back, so the value the head borrows is nobody's.

```text
SpecializationDeclarationError: … code(s) ['first'] are named by the head but no alternative declares them
```

**Repair**: add the reverse `Generalization` field. See `30_error_no_reverse`.

## Two heads claim one alternative

What it looks like: one class is named in two heads' unions, so its value would select two tables.

```text
SpecializationDeclarationError: … class 'FirstPressSpecEntity' is an alternative of 'OtherRecordCoreEntity.pressing'
and of 'VinylRecordCoreEntity.pressing'
```

**Repair**: give each head its own alternatives. See `34_error_two_heads`.

## A class points at the axis without being named

What it looks like: a class has a reverse field into the head but is not in the union — the closure rule.

```text
SpecializationDeclarationError: … class 'UnlistedPressSpecEntity' points at 'pressing' without being named
in the union — add it to the alternatives or remove its reverse field
```

**Repair**: add it to the union, or remove its reverse field. See `35_error_outside_alternative` and `38_error_axis_subset`.

## A value belongs to another dictionary

What it looks like: the alternative names a value of a different dictionary, which the head does not borrow.

```text
SpecializationDeclarationError: … alternative 'FirstPressSpecEntity' names a value … that
'VinylRecordKindEnumEntity' does not declare
```

**Repair**: name a value of the head's dictionary. Covered by `test_entity_specialization_vocabulary`.

## The value disagrees with the loaded row

What it looks like: the container says `variant=VinylRecordKindEnumEntity.EARLY` and holds a `RepressSpecEntity`.

```text
Value error, variant 'early' does not match RepressSpecEntity, which declares 'repress'
```

**Repair**: make the value and the class agree. See `08_specialization_mismatched_data`.

## A stored code arrives bare

What it looks like: a row is built from stored data with `variant="early"`, and the resource passed the code straight through.

```text
Value error, VinylRecordKindEnumEntity: a bare code is not accepted; pass the declared value
or its reference object {'code', 'display_name', 'properties'}
```

**Repair**: resolve the code in the resource, then hand the model the declared value or its reference object. See `07_specialization_data_codes`.

## The marker is given a code list

What it looks like: `Classifier("media", ["first"])`, or the retired `Classifier(field="media", codes=Literal["first"])`.

```text
TypeError: Classifier: variant must be a declared dictionary value, got list: ['first']
```

**Repair**: name a value. See `41_error_codes_not_literal`.

## What is no longer a rule

Five refusals went away with the classifier field, and their experiments with them: a code the classifier's type cannot hold, a classifier that is a relation, a classifier that is not a field, a classifier naming the axis itself, and two axes decided by one field. A head has no classifier field, so a field that does not exist cannot be wrong. Two axes on one head are ordinary now, and `11_specialization_two_axes` is a working example of three of them.
