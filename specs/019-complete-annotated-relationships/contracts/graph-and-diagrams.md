# Contract: Ordinary Association Projection for Dictionary Fields

**Source**: [Specification](../spec.md), FR-014 and graph contract.

## New graph output

For each validated graph-visible AssociationOne[D] field:

| Export item | Value |
| --- | --- |
| source_id / target_id | Host / dictionary full graph identifier |
| type | entity_relation |
| relationship | Existing ordinary association relationship value |
| is_dag | false |
| properties.field_name | Declared field name |
| properties.relation_type | association |
| properties.cardinality | one |
| properties.description | Declared field description |
| properties.has_inverse | false |
| properties.deprecated | Existing ordinary field deprecation value |
| properties.inverse_entity_id / inverse_field | Omitted |

The existing entity_relation schema applies. Required/nullable declarations produce the same edge. A runtime null does not remove declaration-level structure.

Retain one entity_field row for this dictionary association, including reference_qualname equal to the edge target id. Do not retain ordinary structural scalar rows merely as a side effect. No new-source entity_reference edge and no duplicate entity_relation edge are allowed. NoGraphEdge keeps existing supported presentation behavior after validation.

## Maxitor output

Use the ordinary relation path: host source, dictionary target, relationship_kind association, ordinary field/cardinality label, source_cardinality zero_many and target_cardinality one. Keep the dictionary catalogue card, descriptive values and reference type hint. Determine dictionary identity from the target stereotype. Do not synthesize a second arrow from reference_qualname.

Include cross-domain target/neighbour slicing checks so a valid dictionary target is not dropped just because the old special-reference path is no longer used.

### One dictionary field row in the diagram payload

For every selected host dictionary field, return exactly one item in the entity's `fields` list keyed by `(entity_id, field_name)`. The retained graph field row is authoritative for `field_id`, `name`, `type`, `primary_key`, ordering ordinal and `reference_qualname`.

When an ordinary dictionary association edge in the loaded graph matches that host, field and dictionary target, enrich this retained row with `foreign_key=true`; do not append the ordinary synthesized FK row for the same key. Matching must use the owner and field, not the dictionary target alone: two fields selecting the same catalogue remain two distinct rows. Target-card slicing must not erase the field identity/hint or create a second row. Association arrows still obey the ordinary selected-entity/neighbour rules.

Keep the retained row's original position among fields. In particular, do not replace its field_id with null, its type with the synthesized `FK -> ...` text, or its ordinal with the fallback FK ordinal. Existing rendering can use reference_qualname to show the dictionary type hint.

Where an ordinary structural relationship has no retained field row, preserve the existing synthesized FK-row behavior. Historical special-reference input keeps its existing payload semantics. With NoGraphEdge, do not synthesize an association or FK marker merely from reference_qualname; retain the supported field presentation and no-arrow behavior.

Current SQL UNION ALL/SELECT DISTINCT is not sufficient for the new dictionary case: the retained and synthesized rows have different field_id/type/ordinal values. Join/enrich or suppress the matching fallback row before field aggregation; do not rely on full-row DISTINCT.

Acceptance must assert `count(fields where name == "region") == 1`, the preserved field_id/type/order/reference_qualname, `foreign_key=true` when the matching ordinary association is present, one arrow, stable behavior with target-card slicing, separate same-dictionary fields and unchanged structural fallback/historical controls.

## Historical input

Keep the legacy entity_reference JSON-schema definition and DuckDB loader/table for historical files. Dedicated legacy-import controls may still expect legacy reference payload semantics. New model-generated fixtures/snapshots use entity_relation association semantics. Historical import cannot make bare source declarations legal or cause an extra arrow for one new declaration.

## Acceptance partitions

Assert exact new edge properties, ordinary schema validation, retained row/hint identity, nullable shape stability, omitted inverse ids, deprecation metadata, NoGraphEdge controls, dictionary card preservation, neighbour selection, one enriched field row per dictionary field with preserved identity/order, no duplicated arrow and a separate historical-input control.
