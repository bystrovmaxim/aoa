# US1 Evidence: Complete Declaration Enforcement

**Task**: T013 (Procedure 3 — US1)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## What landed

`validate_entity_fields` now enforces the complete semantic declaration on every `@entity`
host — including graph-excluded hosts — instead of accepting bare entities, bare dictionaries
and `NoRelation`. The relation resolver reads the normalized descriptor from
`resolved_entity_fields` and no longer re-runs `get_type_hints`. A direct
`EntityGraphNode` projection runs the same gate.

## Commands and results

US1-focused partitions, all in importlib mode from the repository root:

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/intents/entity/test_resolved_entity_fields.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_source_check.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_declaration_entrypoints.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_unchanged_controls.py -q
```

```text
81 passed
```

Source gate (explicit permitted roots only):

```sh
.venv/bin/python scripts/check_complete_entity_fields.py examples/step_21_relations/
# 0 violations (the existing examples already use a single assignment-side Field)
```

## Per-stereotype coverage

| Stereotype | Complete form accepted | Incomplete forms refused |
| --- | --- | --- |
| Core | `AssociationOne[T], Inverse` / `AssociationMany[T], NoInverse` | bare, nullable bare, bare `Annotated`, list/set/tuple, mapping, union, mixed collection, `NoRelation`, missing/duplicate/conflicting direction markers, blank description, invalid default |
| Assoc | dictionary target refuses bare form on Assoc host | same universal rule |
| Detail | dictionary target refuses bare form on Detail host | same universal rule |
| Spec | `Specialization` head + `Generalization` alternative (spec validator unchanged) | bare dictionary on Spec host, `Generalization[D]` |
| Enum | `AssociationOne[D] \| None, NoInverse` | bare `D`, `D \| None`, collection, union of dictionaries, `AssociationMany[D]`, `CompositeOne[D]`, `Generalization[D]`, `Inverse` on a dictionary, empty catalogue, dictionary outside the graph |
| State | unchanged Lifecycle contract | bare State field, State in container, State with marker |

Each non-State case is exercised independently as owner and target where permitted.

## Source spelling vs runtime semantics

- Runtime semantics are enforced by `validate_entity_fields` from the completed
  `FieldInfo.annotation` / `FieldInfo.metadata`; it works without source files.
- Source placement (one assignment-side `Field(...)`, none inside `Annotated`) is enforced
  separately by `scripts/check_complete_entity_fields.py` (AST, explicit roots). The two are
  complementary; neither claims the other's guarantee.

## No graph-exclusion escape

`test_a_graph_excluded_host_is_still_judged` proves an `@exclude_graph_model` host with a
bare entity field is still refused by the global pass. `test_direct_entity_graph_node_projection_is_refused`
proves the same for direct projection, and `test_coordinator_build_refuses_an_invalid_declaration`
for the coordinator/factory path.

## Known remaining migration (not part of US1)

The completeness gate now refuses bare-dictionary fixtures in files that US3/US5 migrate:
`packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`,
`test_entity_field_graph.py`, `test_dictionary_core_schema.py`, `test_dictionary_json_schema.py`
and several runtime/graph fixtures that still declare the old bare-dictionary or incomplete
form. Their graph projection changes (`entity_reference` → `entity_relation`) belong to T027/T028,
so those files are intentionally left failing under this gate until US3/US5. The six-file
baseline's `test_entity_field_validator.py` portion is green; the reference-graph file fails on
the new rule by design and is migrated in T028.

This is not the closing check run; no full-repository pass is claimed.
