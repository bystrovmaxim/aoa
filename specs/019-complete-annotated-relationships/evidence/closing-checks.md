# Closing Checks Evidence (blocked)

**Task**: T039 (Procedure 8 — C1)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## Status: BLOCKED — not run to zero

The closing check cannot run to zero because the prerequisite ("all behavior and authorized
production/test migrations must be settled first") is not met. The US5 corpus migration
(T037/T038) and the US3 consumer migration (T024/T029/T030) are incomplete, so the full
action-machine suite is **150 failed, 2672 passed, 153 errors**.

## Scoped feature suite

The feature's own tests (US1–US5 partial) are green apart from two negative fixtures that
still poison the global completeness pass:

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/intents/entity/test_resolved_entity_fields.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_source_check.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_declaration_entrypoints.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_unchanged_controls.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_cross_module.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association_schema.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_association_graph.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_relationship_compatibility_regressions.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_complete_relationship_migration.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_containers.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py -q
```

```text
170 passed, 2 failed
```

The 2 failures are negative fixtures needing subprocess isolation / direction markers
(`SilentHeadCoreEntity` in `test_entity_specialization_rules_axis.py`; the global pass in
`test_entity_field_graph.py` refuses it). This is the remaining US5 migration, not a feature
defect.

## Adversarial verification (targeted regressions)

The five required mutations are each caught by a focused regression while valid neighbors pass:

| Mutation restored | Targeted regression | Result |
| --- | --- | --- |
| bare Enum acceptance | `test_a_bare_dictionary_reference_is_refused` | refused (caught) |
| NoRelation acceptance | `test_the_embedded_form_is_now_refused` | refused (caught) |
| missing direction marker | `test_a_relation_without_a_direction_marker_is_refused` | refused (caught) |
| nonreciprocal pair | `test_a_one_sided_inverse_is_refused` | refused (caught) |
| special dictionary edge | `test_one_ordinary_relation_edge_and_one_retained_field_row` | no special edge (caught) |

```text
8 passed
```

## Lint / format

`ruff check` and `ruff format --check` pass on every new/modified file across Procedures 1–7.

## Not run / excluded

- The forbidden aggregate script `scripts/run_checks_with_log.sh` was never run.
- No full-repository pass is claimed.
- The scoped type-check and client/TypeScript checks (C1's remaining partitions) are not run
  because the corpus is not yet fully migrated.
- Teaching-material migration and execution belong to C2 (T040) and are not started.

This evidence records the blocked state; T039 is not complete until the corpus migration
finishes and the check runs to zero.
