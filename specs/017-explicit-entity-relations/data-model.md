# Data Model: the field declaration, the marker, the relation metadata, the member, the schema and the card

**Feature**: `specs/017-explicit-entity-relations` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md)

The change models six things: a field whose type is an entity, the marker that refuses a relation, the metadata a relation field carries, a dictionary member after user validation, the serialization schema of a dictionary, and the two row shapes on an ERD card. Nothing is persisted differently, and the graph document keeps the code and the label it already carries.

## Entity field declaration

One annotated line in a model body, judged by its resolved type.

| Aspect | Rule |
| --- | --- |
| Structural entity | a `BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity` or `BaseStateEntity` descendant |
| Dictionary reference | a `BaseEnumEntity` descendant, optionally `Optional` — a bare type, no marker |
| Lifecycle reference | a `Lifecycle[...]` descendant carried on a field — a bare type, no marker |
| Schema type | a `BaseSchema` descendant (`Params`, `Result`, `State`) — outside the rule, never in the ERD |
| Legal form 1 | a relation container of the eight: `AssociationOne`/`Many`, `CompositeOne`/`Many`, `AggregateOne`/`Many`, `Specialization`, `Generalization` |
| Legal form 2 | `Annotated[Entity, NoRelation("reason")]`, optionally with `\| None` |
| Refused | a bare entity, a bare `X \| None`, a collection (`list`, `dict`, `set`, `tuple`) of an entity, and any state entity in any of those forms |
| Where it is judged | the graph-build boundary, on the resolved annotation |
| Forward reference | judged after resolution; an unresolvable name keeps its existing failure |

## Embedded-value marker

| Aspect | Rule |
| --- | --- |
| Form | `NoRelation("reason")` inside `Annotated` |
| Reason | a nonblank string; a blank or missing reason is refused at construction |
| Applies to | Core, Assoc, Detail and Spec only — a state has no field form, so the marker is refused there |
| Effect | the field stays an ordinary column; no relation edge, no foreign key, no storage inference, no change to nested validation |
| Not to be combined with | a relation container, `Inverse`, `NoInverse`, `NoGraphEdge` |
| Visibility | the declaration only — the graph, the payload and the card carry no extra member |
| Contrast | `NoGraphEdge()` hides the edge of a relation that exists; `NoRelation` states that no model relation exists |

## Relation field metadata

The contract for the eight containers, checked at the same boundary.

| Annotation and declaration | Omitted input (complete entity) | Explicit `None` |
| --- | --- | --- |
| `Relation[T] = Field(description=…)` | missing-field error | refused |
| `Relation[T] \| None = Field(description=…)` | missing-field error | accepted |
| `Relation[T] \| None = Field(default=None, description=…)` | `None` | accepted |
| `Relation[T] = Field(default=None, description=…)` | declaration refused | declaration refused |

| Aspect | Rule |
| --- | --- |
| Description source | `FieldInfo.description` only, nonblank; both supported syntaxes merge into it |
| Default | absent, or an explicit `None` when the annotation allows it |
| Refused defaults | every other value, including a prebuilt container and any description-shaped object |
| `default_factory` | refused on a relation field, and never executed |
| Partial instance | unaffected — constructed from any subset of non-key fields, reporting an unloaded field on access |
| Hidden edge | `NoGraphEdge()` changes nothing about these rules |

## Dictionary member

| Aspect | Rule |
| --- | --- |
| Identity | `(dictionary type, code)`; the class attribute is where it is reachable |
| Annotation rule | unchanged: `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `time`, `UUID`, `Literal`, `Optional` of a supported type, tuples of supported types, and `Enum` |
| Runtime rule (new) | the completed value's type must agree with the declared annotation and satisfy the immutable set recursively |
| `Enum` values | the member's own value obeys the same set recursively; a list, mapping, set or model instance as an enum value is refused |
| Refusal | names the dictionary, the member, the property path, the expected type and the actual type — the value is never frozen, coerced or re-annotated |
| Publication | a refused member is never assigned to `members`, `codes()` or `by_code()` |
| Export | unchanged — `to_reference()` is the JSON export, and editing an export never reaches the declared tuple |

## Dictionary serialization schema

| Aspect | Rule |
| --- | --- |
| Top shape | `{code, display_name, properties}` with `additionalProperties: false` and the three members required |
| `properties` | an object declaring each emitted property by name, refusing additional members |
| `properties.required` | derived from the emitted document: a value emitted as `null` is required and nullable; an excluded field is not required |
| Definitions | every referenced definition is present in `$defs`; two classes with the same short name keep distinct definitions |
| Emission mode | serialization — a custom serializer's output type is what the schema describes |
| Input schema | unchanged: accepts a code-only reference and a full reference, and does not require `display_name` or `properties` |
| Contract split | the two schemas remain separate; this change does not make them identical |

## ERD dictionary card

| Aspect | Rule |
| --- | --- |
| Payload fields (enum kind) | `code` and `display_name` rows omitted; the dictionary's own declared property rows remain |
| Payload fields (other kinds) | unchanged |
| Value row | the label, then the value's properties as `name: value` lines |
| Code | present in the graph document, in its schema and in the payload's `properties.values`; exposed as a `TOOLTIP` on the row; never printed |
| Escaping | labels, property names and values stay escaped; the tooltip text is escaped the same way |
| Old graphs | a graph saved with the code and label rows renders without a rebuild |

## Relationships between the six

- A **field declaration** carries either a **relation container** or the **embedded-value marker**; the marker is what makes the second form legal.
- A **relation field** carries a runtime value and **metadata** (the description); the two never mix, which is the whole of the default contract.
- A **dictionary member** is published only after its runtime type and its **`Enum` values** have been verified; the verified member is what the **serialization schema** must describe.
- The **card** is a projection of the graph: it reads the member, prints the label, and hands the code to a tooltip, without becoming a second source of truth.
