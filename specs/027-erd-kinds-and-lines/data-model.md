# Data Model: Entity Kinds Travel with the Graph, and the ERD Shows Every Line It Should

## Kind

| Field | Where it lives | Rule |
|---|---|---|
| word | `Entity` node `properties.entity_kind`; DuckDB `entity.entity_kind` | Required on the wire, `^[a-z][a-z0-9_]*$`. AOA derives it from the kind base's class name. Maxitor stores a missing or blank value as `unknown`. |
| display name | `Entity` node `properties.entity_kind_label`; DuckDB `entity.entity_kind_label` (nullable) | Optional on the wire, non-empty when present. AOA always writes it. Maxitor lists the smallest non-blank one per word, else the word with its first letter capitalised. |

A graph contains a set of kinds; neither AOA nor Maxitor fixes it. `state` is a valid word that AOA never writes on an `Entity` row.

## Kind base (AOA)

A class that inherits `BaseEntity` directly and defines its own `__init_subclass__`.

| Attribute | Rule |
|---|---|
| name `Base<Word>Entity` | The word is the name without `Base` and `Entity`, lower-cased (unchanged). |
| `KIND_LABEL: ClassVar[str]` | **New.** Declared in the class's own body, non-empty after stripping; checked at class creation (`DeclarationStructureError` naming the class otherwise). |

The six: `BaseCoreEntity` Core, `BaseAssocEntity` Association, `BaseDetailEntity` Detail, `BaseSpecEntity` Specialization, `BaseEnumEntity` Enumeration, `BaseStateEntity` State.

## Association (Maxitor relation row)

One relation between two tables: a relation field and, when declared, its inverse.

| Field | Meaning |
|---|---|
| `source`, `target` | Table ids; `source` holds the canonical field (the `one` side; ties → smaller id, then smaller field name). |
| `source_field` | **New.** The canonical field on `source` pointing at `target`; the role written at `target`'s end. |
| `target_field` | **New.** Its inverse on `target`, or `null`; the role written at `source`'s end. |
| `source_cardinality`, `target_cardinality` | `one` or `zero_many`; drawn as a bar or a crow's foot at that end. |
| `relationship_kind` | `association`, `composition`, … as today; `reference` for dictionary references; `generalization` and `specialization` keep their meaning and are never paired. |
| `label` | Kept for other consumers; not drawn for associations. |

Uniqueness: one row per association per list. Pairing condition: `i.source = r.target`, `i.field = r.inverse_field`, `i.target = r.source`.

## Line

What the ERD draws for an association, a reference (including a specialization head's link to the dictionary of its axis) or a generalization whose two ends are both on screen. Derived, never stored. Its hover state marks the rows of `source_field` and `target_field` (or the target's key rows).

## Filter state (client, per diagram)

| Field | Rule |
|---|---|
| domains switched off | As today (`enabledDomainsByDiagramKey`, or entity qualifiers in the single-domain view). |
| kinds switched off | **New.** `enabledEntityKinds`, persisted per `diagramResetKey`; every kind on for a new diagram. |
| open panel section | Not persisted; `domains` when the diagram mounts. |

Visibility: a table is on screen ⇔ its domain (or qualifier) is on ∧ its kind is on. Lines and containers are pruned once, after the table filter.
