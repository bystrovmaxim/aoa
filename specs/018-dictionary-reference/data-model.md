# Data Model: the dictionary reference, the edge, the row and the refusal

**Feature**: `specs/018-dictionary-reference` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md)

The change models four things: a field whose type is a dictionary, the graph edge that carries the reference, the field row the ERD keeps beside it, and the refusal text. Nothing is persisted differently and no storage column changes.

## Dictionary reference field

One annotated line in a model body, judged by its resolved type at the declaration boundary.

| Aspect | Rule |
| --- | --- |
| Kind | a `BaseEnumEntity` descendant — a closed dictionary |
| Accepted form 1 | `D` |
| Accepted form 2 | `D \| None` |
| Refused | a collection (`tuple`, `list`, `Sequence`, `set`, `frozenset`, `dict`) of `D` |
| Refused | any of the eight relation containers whose argument is `D` |
| Refused | `Annotated[D, NoRelation("…")]` |
| Refused | `D` whose catalogue is empty |
| Refused | `D` that is not a graph model (`@entity`, not `@exclude_graph_model`) |
| Precedence | an empty catalogue is reported before the not-a-graph-model refusal, because `@entity` already refuses an empty dictionary and the author can only fix the catalogue |
| Where it is judged | the declaration boundary, before the graph's referential-integrity pass |
| Forward reference | judged after resolution |
| Inherited field | judged on the class that reports it in `model_fields` |

| Written | Answer |
| --- | --- |
| `currency: CurrencyEnumEntity` | accepted as the reference; no refusal |
| `currency: CurrencyEnumEntity \| None` | accepted on the same terms |
| `currencies: tuple[CurrencyEnumEntity, ...]` | refused: a collection has no declared form; the message shows the two accepted ones |
| `currency: AssociationOne[CurrencyEnumEntity]` | refused: a dictionary value is a shared reference, not an association target |
| `currency: Annotated[CurrencyEnumEntity, NoRelation("…")]` | refused: the bare type already declares the reference |
| `currency: EmptyEnumEntity` | refused: the dictionary declares no values |
| `currency: ExcludedEnumEntity` (no graph node) | refused: the reference could not be drawn |

## Reference edge

One outgoing edge per accepted reference, emitted while the host's entity node is built.

| Property | Value |
| --- | --- |
| `edge_name` | `entity_reference` |
| `relationship` | `association` (the edge's fixed relationship) |
| `is_dag` | `false` |
| `source_id` | the host entity's interchange id |
| `target_id` | the dictionary's interchange id |
| `properties.field_name` | the field that declares the reference |
| `properties.cardinality` | `one` — every accepted form holds one value |

The edge carries no `description`, `inverse`, `has_inverse` or `deprecated`: a reference has none of them, and the field's description stays on the field.

## Field row

The `entity_field` node and edge stay exactly as #249 left them.

| Aspect | Rule |
| --- | --- |
| Row | one `entity_field` per scalar field, the dictionary reference included |
| `field_type` | the annotation, rendered as today |
| `reference_qualname` | the dictionary's interchange id, for every accepted form |
| Relation to the edge | the row and the edge describe the same fact — the code column and the link — and neither replaces the other |

## ERD relation row

One payload entry per reference, produced by `list_entities_action` from the new DuckDB table.

| Key | Value |
| --- | --- |
| `source` | the host entity id |
| `target` | the dictionary id |
| `label` | the field name |
| `relationship_kind` | `reference` |
| `source_cardinality` | `one` |
| `target_cardinality` | `zero_many` |

The row is drawn by the existing relation loop: any kind other than `specialization` becomes an arrow with its label. The dictionary card keeps #249's shape — no `code` row, no `display_name` row, no code cell in a value row, the code in a tooltip — so the reference appears once as the row's `→ Dict` text and once as the arrow label, which is the field name.

## Refusal

| Aspect | Rule |
| --- | --- |
| Names | the owner, the field and the resolved type |
| Shows | the form that fits: the two dictionary forms, or the shape the author wrote |
| Union of two structural entities | names both entities and asks for separate fields |
| Heterogeneous collection | names the collection and every entity it holds |
| Mapping | describes a mapping, and does not offer a many-relation |
| Behaviour | text only — none of the three shapes becomes accepted |

## Relationships between the four

- A **dictionary reference field** produces exactly one **reference edge** and keeps its **field row**; a refused field produces neither.
- The **reference edge** is projected into the ERD as one **relation row**; the **field row** is projected as today.
- The **refusal** is the only outcome for a shape that has no reference: it names the field and the forms, and never reaches the edge or the row.

## Invariants

- One dictionary reference field ⇒ one `entity_reference` edge, one field row with `reference_qualname`, one ERD relation with kind `reference`.
- Zero refused forms reach the graph: a build with any refused dictionary field fails before referential integrity.
- The reference edge's target is always a node of the same published graph.
- The ERD never prints the same reference text twice: the row prints the dictionary, the edge prints the field name.
