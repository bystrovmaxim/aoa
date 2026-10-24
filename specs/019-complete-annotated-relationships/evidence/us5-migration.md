# US5 Evidence: Corpus Migration (partial)

**Task**: T038 (Procedure 7 — US5)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## Status

The migration is **in progress**. T035 and T036 are complete; T037 is partially complete. This
record is honest about what migrated and what remains.

## Migrated

- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py`
  — `ReferenceTagCoreEntity.currency` / `settlement_currency` moved from bare dictionary to
  `Annotated[AssociationOne[ReferenceCurrencyEnumEntity] | None, NoInverse()]`; the dictionary
  is no longer `@exclude_graph_model`. Field-row assertions unchanged (8 passed).
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`
  — all bare dictionary fields (`currency`, `settlement`, `first`, `second`, `kind`) moved to
  `AssociationOne[D] | None` with `NoInverse()`; dictionaries are in-graph; the test assertions
  migrated from the retired `entity_reference` edge to the ordinary `entity_relation` edge
  (`node.references == []`, `node.relations` carries `relation_type=association`,
  `cardinality=one`, `has_inverse=false`). 11 passed.

## Production audit (T036)

No production entity declaration needs migration. The only production entity host is
`packages/aoa-maxitor/src/aoa/maxitor/model/core/entities/node_entity.py`, which declares
scalar fields only. The library source references the new forms only in validators/docstrings,
not in user declarations.

## Remaining migration (not yet done)

- `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py`
  and `test_dictionary_json_schema.py` — `SchemaPriceTagCoreEntity` and similar hosts still
  declare bare dictionary fields; they must become `AssociationOne[D]` (value construction moves
  to explicit wrappers) or be re-scoped to the standalone dictionary VALUE API.
- `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py`
  — historical reference-edge assertions must become historical-import controls.
- Specialization fixtures missing direction markers in
  `test_entity_specialization_rules_axis.py` (`SilentHeadCoreEntity`), `..._sweep.py`,
  `..._graph.py` and `..._vocabulary.py`.
- `packages/aoa-action-machine/tests/support/domain_model` and other graph/runtime fixtures
  that still carry a bare target, a `NoRelation` alternative or a missing/one-sided marker.
- Negative-test fixtures (`@exclude_graph_model @entity` with intentionally invalid
  declarations, e.g. `HiddenReferenceCoreEntity`) must be subprocess-isolated like the
  `test_entity_field_validator.py` fixtures, so the global completeness pass stops refusing them.

Full-suite status after the partial migration: **150 failed, 2672 passed, 153 errors** (down
from 163 failed at the start of US5). The remaining failures are contamination from the
un-migrated fixtures above; each must be migrated or isolated before the closing check.

## Source gate

`scripts/check_complete_entity_fields.py` is not run over the test corpus here because the
test fixtures are not yet fully migrated; it was verified in T005/T007 on explicit roots.

## Regression tests (T035)

`packages/aoa-action-machine/tests/action_machine/graph/test_complete_relationship_migration.py`
(3 passed) pins the before/after behavior: bare dictionary → `AssociationOne[D]`,
`NoRelation` → complete relationship, one-sided inverse → reciprocal markers.
