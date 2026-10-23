# Contract: a refusal names the shape that is wrong

**Feature**: `specs/018-dictionary-reference` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

Three shapes refuse today with a message about a different shape. This contract fixes the wording only: none of the three becomes accepted, and every other refusal keeps its behaviour.

## 1. What is wrong today

| Written | Today | Required |
| --- | --- | --- |
| `A \| B` for two structural entities | "a collection of an entity (A \| B)" and `AssociationMany[A]` | names both entities and asks for two fields |
| `tuple[A, B]` for two different structural entities | "a collection of an entity (tuple)" and `AssociationMany[A]` | names the collection and both entities; no single-target advice |
| `dict[str, A]` | "a collection of an entity (dict)" and `AssociationMany[A]` | describes a mapping and offers a form that fits |

## 2. The shape classifier

| Shape | Recognized by | Message names |
| --- | --- | --- |
| bare entity | the resolved type is an entity | the entity, the two legal forms |
| optional entity | one non-`None` member, `None` allowed | the entity, the `\| None` form |
| union of entities | a union with two or more entity members | every entity, and that a field states one form |
| homogeneous collection | a container whose members are one entity | the container and the entity |
| heterogeneous collection | a container with two or more entities | the container and every entity |
| mapping | a mapping whose value is an entity | the mapping and the entity |

| Rule | Statement |
| --- | --- |
| One classifier | the shape is classified once and the message is derived from it |
| Owner and field | every refusal names both, as today |
| No advice that does not fit | a union is never told to use `AssociationMany`; a mapping is never told to use it either |
| Behaviour | unchanged: every one of these shapes was and stays refused |
| Dictionary | a collection of dictionary values takes the dictionary message, not this one |

## 3. The three messages

```text
OfferCoreEntity.ref: the field's type is a union of two entities (A | B), so the field states
two possible relations at once. Declare one field per entity, each with its own form.

OfferCoreEntity.ref: the field's type is a collection of two entities (tuple[A, B]); a
collection is not a relation. Declare one field per entity, each with its own form.

OfferCoreEntity.ref: the field's type is a mapping from str to A, and a mapping is not a
relation. Declare the relation on the owning entity, or model the mapping as its own entity.
```

The exact words are the implementation's; the contract fixes the three facts each message must state: the shape, the entities it holds, and the form that fits.

## 4. What does not change

| Case | Behaviour |
| --- | --- |
| a bare structural entity | refused as today, with the two legal forms |
| a bare `X \| None` | refused as today |
| a homogeneous collection | refused as today, with the many-relation form |
| a state entity in any form | refused with the `Lifecycle[...]` form |
| a dictionary collection | refused with the dictionary form table |
| a relation container and `NoRelation` together | refused as today |
