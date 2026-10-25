# Data model — the dictionary, its values and the card

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-25

The change moves no data. This page fixes what each layer carries, so "the graph keeps everything" is a statement with a shape rather than a promise.

## 1. The graph document

A dictionary is a node whose `properties.entity_kind` is `enum`. It carries its values as references:

```json
{
  "id": "datamodel.offers.region_enum_entity.RegionEnumEntity",
  "label": "RegionEnumEntity",
  "properties": {
    "entity_kind": "enum",
    "values": [
      {"code": "world", "display_name": "Весь мир", "properties": {"is_obsolete": false}},
      {"code": "ru", "display_name": "Россия", "properties": {"is_obsolete": false, "iso_code": "RU"}}
    ]
  }
}
```

| Rule | Statement | Requirement |
| --- | --- | --- |
| Unchanged by this feature | every value keeps `code`, `display_name` and its `properties` | FR-003 |
| Values are not nodes | a value has no identity, domain or edges of its own | unchanged from #241 |
| Order | declaration order | unchanged |

## 2. The ERD payload

The entity endpoint turns the mapping into a typed list, so the payload satisfies its schema:

```json
{
  "id": "…RegionEnumEntity",
  "label": "RegionEnumEntity",
  "entity_kind": "enum",
  "fields": [
    {"field_id": "…:id", "name": "id", "type": "str", "primary_key": true, "foreign_key": false, "reference_qualname": null},
    {"field_id": "…:is_obsolete", "name": "is_obsolete", "type": "bool", "primary_key": false, "foreign_key": false, "reference_qualname": null}
  ],
  "values": [
    {"code": "world", "display_name": "Весь мир", "properties": [{"name": "is_obsolete", "value": "false"}]}
  ]
}
```

| Rule | Statement | Requirement |
| --- | --- | --- |
| Kept | `values` stays, typed as `{code, display_name, properties: [{name, value}]}`, in declaration order | FR-004 |
| Kept | the two storage field rows (`code`, `display_name`) are still absent from `fields` | FR-002, #249 |
| Empty list | a value with no extra properties carries `properties: []` | FR-004 |
| Schema | the payload schema is not edited | FR-004 |

## 3. The card

The card is what the renderer produces from one payload entity. Its parts after this change:

| Part | Content | Source |
| --- | --- | --- |
| Header | entity label, coloured by the domain | `label`, `color` |
| Field rows | one per entity field: key marker (`PK`/`FK`), name, type, and the dictionary name after `→` when the field references one | `fields` |
| Arrows | one per relation, labelled with the field name | `relations` |
| Value rows | **none** | — |

| Rule | Statement | Requirement |
| --- | --- | --- |
| No value row | no label, no property, no code appears for a value | FR-001 |
| No substitute | no badge, count, tint or marker is added | FR-002 |
| Independent of the count | 1 value and 93 values draw the same card | FR-005 |
| No vocabulary | the renderer reads no dictionary name, kind or field name | FR-006 |
| Escaping | field text is escaped once; nothing of the values reaches the SVG | FR-007 |

## 4. What is not modelled here

- **The full graph's nodes.** A dictionary's `code` and `display_name` still appear there as field nodes; that view is outside this feature.
- **The specialization axis.** Its field row still prints `Specialization N+` with a tooltip of alternative codes; unchanged.
- **The graph's schema and the payload schema.** Neither changes, so no migration and no version bump.

## 5. Invariants that the checks must be able to break

| Invariant | Break that must fail a check |
| --- | --- |
| No value text reaches the DOT | re-render `valueRows` with one value |
| The card does not depend on the values | render the same entity with and without `values`; DOT must be equal |
| The graph still carries the values | drop `values` from the export; the graph test must fail |
| The payload still carries the values | drop `values` from the payload; the payload test must fail |
| A non-dictionary card is unchanged | move a field row into the dictionary-only branch |
