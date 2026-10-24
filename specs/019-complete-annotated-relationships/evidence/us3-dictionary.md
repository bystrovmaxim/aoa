# US3 Evidence: Explicit Dictionary Association

**Task**: T031 (Procedure 5 — US3)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## What landed

`AssociationOne[D]` now has a dictionary-specific Pydantic core/JSON schema: Python input
requires an explicit wrapper and normalizes it to a new frozen wrapper holding the canonical
member; JSON input accepts only the `{id: code}` object; JSON output is the member's
`to_reference()`. The declaration rule accepts only `AssociationOne[D] | None` with
`NoInverse()`. The graph projects one ordinary `entity_relation` edge plus one retained
`entity_field` row (`reference_qualname` = the dictionary), with no special `entity_reference`
edge for new declarations.

## Commands and results

Runtime, schema, graph and controls (importlib mode):

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association_schema.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_association_graph.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_containers.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py -q
```

```text
44 passed
```

## Real outcomes

- Python id-only: `AssociationOne(id="eur")` → `field.entity is CurrencyEnumEntity.EUR`,
  `field.id == field.entity.code`.
- Python id + identity-matching member: accepted; a copy or a mismatched member is refused.
- Unknown id, non-string id, raw member, bare code and Python mapping are all refused.
- The input wrapper is not mutated; the validated field receives a new wrapper.
- JSON `{"id": "eur"}` resolves the canonical member; extra keys and the old reference shape
  are refused.
- JSON output equals `to_reference()` (including a custom `field_serializer` date).
- Validation schema: `{type: object, required: [id], properties: {id: string}}`; serialization
  schema: `{required: [code, display_name, properties]}`. The asymmetry is deliberate; direct
  output-to-input round-tripping is not promised.
- Graph: one `entity_relation` edge (`relation_type=association`, `cardinality=one`,
  `has_inverse=false`) plus one retained `entity_field` row with `reference_qualname` equal to
  the dictionary's graph identifier; `node.references == []`.

## Not yet delivered (consumer migration)

The Maxitor consumer work is deferred to a follow-up and is **not** claimed here:
- T024 (`packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py` ordinary
  association fixtures and one-enriched-field-row assertion).
- T029 (`list_entities_action.py` / `duckdb_graph_resource.py` row enrichment by
  `(entity_id, field_name)`).
- T030 (`check-erd-dictionary-values.ts` renderer check).

These require the Maxitor package's Python/TypeScript surface and are the remaining US3
scope. The action-machine runtime/schema/graph slices are complete and green above.
