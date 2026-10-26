# Contract: relation rows in `GET /api/v1/list-entities`

Owner: `aoa-maxitor`, `ListEntitiesAction` + `list_entities_action_schema.py`. Additive: existing fields keep their names and types.

## Which rows a list holds

- **Per slice** (`domain_slices[i].list_entities.relations`): every relation, dictionary reference and generalization whose **both ends** are in that slice's selected entities (its domain, plus 1-hop neighbours when asked); no condition on the slice's own domain. Specialization rows (head → container) as today.
- **Request-wide** (new, top level `relations` beside `domain_slices`): the same rows over the union of all requested slices' selected entities. The merged multi-domain ERD draws this list, pruned to tables on screen.

A **specialization axis** whose dictionary (`dictionary_qualname`) is among the list's entities adds one row from the head to the dictionary: `relationship_kind: "reference"`, `source_field` = the axis field (`kind`), `target_field: null`, `source_cardinality: "zero_many"`, `target_cardinality: "one"`.

## Row shape

```json
{
  "source": "datamodel.players.player_core_entity.PlayerCoreEntity",
  "target": "datamodel.showcases.showcase_core_entity.ShowcaseCoreEntity",
  "source_field": "showcase",
  "target_field": "players",
  "source_cardinality": "zero_many",
  "target_cardinality": "one",
  "relationship_kind": "association",
  "label": "showcase (one)"
}
```

| Field | Rule |
|---|---|
| `source_field` | **New**, required for association and reference rows: the canonical field. |
| `target_field` | **New**, string or `null`: the inverse field. `null` for references, generalizations and relations without an inverse. |
| pairing | a field and its declared inverse give **one** row; a relation without an inverse is its own row |
| canonical side | the side whose field has cardinality `one`; for one-one / many-many the smaller `source` id, then the smaller field name |
| cardinalities | `target_cardinality` from the canonical field (`one` → `one`, `many` → `zero_many`); `source_cardinality` from the inverse, or today's derived value without one |

On the reference graph (`specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz`), all four domains requested: 34 association rows from 46 relation fields; one table pair (`OfferRequestCoreEntity`, `OfferRequestItemDetailEntity`) has two.

## FK rows in `fields`

An FK row's `type` is the target table's label (`"ShowcaseCoreEntity"`), no longer `"FK -> ShowcaseCoreEntity"`; `foreign_key: true` is unchanged.
