# US2 Evidence: Reciprocal Inverse Declarations

**Task**: T020 (Procedure 4 — US2)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## What landed

`entity_inverse_validator.py` requires every ordinary relation field that declares
`Inverse` to name a reverse field that exists on the resolved target, declares its own
`Inverse` and names the originating endpoint back by canonical
`(declaring_owner_class_identity, field_name)`. The field-only
`Inverse(field_name=...)` resolves its target from the container; a concrete
`Inverse(Target, "field")` must match the resolved target by identity. `NoInverse()`
remains an unpaired declaration and can never be a claimed reverse. Specialization heads
and alternatives keep their own reciprocal contract in the specialization validator.

## Commands and results

US2 + markers + US1 controls, importlib mode from the repository root:

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_cross_module.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_containers.py \
  packages/aoa-action-machine/tests/action_machine/intents/entity/test_resolved_entity_fields.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_source_check.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_declaration_entrypoints.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_unchanged_controls.py -q
```

```text
116 passed
```

## Real outcomes

- Field-only reciprocal pair passes: `Region.offer = Annotated[AssociationOne[Offer], Inverse(field_name="regions")]`
  paired with `Offer.regions = Annotated[AssociationMany[Region], Inverse(field_name="offer")]`.
- Concrete-class reciprocal pair passes with `Inverse(Offer, "regions")` / `Inverse(Region, "offer")`.
- One-sided inverse is refused; the reverse field is reported as declaring "no Inverse".
- A concrete target that does not match the resolved container target is refused:
  `the concrete Inverse target (OtherCoreEntity) does not match the resolved container target (OfferCoreEntity)`.
- Unchanged inherited `Base.items` ↔ `Item.owner` keeps the base endpoint; a `Child` override that
  still points at the base pair is refused.
- Cross-module: both import orders resolve through the composition root's explicit
  `model_rebuild(_types_namespace=...)`; an unresolved name blocks assembly before it is read
  as a scalar.

## Known remaining migration (not part of US2)

The completeness gate (US1) and the inverse gate (US2) now refuse old-style specialization and
reference fixtures that declare no direction marker or a bare dictionary. Their migration is
US5 (T036/T037): `test_entity_specialization_rules_axis.py` (two head fixtures),
`test_entity_specialization_sweep.py`, `test_entity_specialization_graph.py`,
`test_entity_reference_graph.py`, `test_entity_field_graph.py`, `test_dictionary_core_schema.py`
and `test_dictionary_json_schema.py`. This is not the closing check run; no full-repository
pass is claimed.
