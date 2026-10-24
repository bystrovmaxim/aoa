# Migration Inventory: Complete Annotated Relationships

**Task**: T001 (Procedure 1 — Setup and scoped evidence)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2` (`Merge pull request #257 from bystrovmaxim/feature/issue-256-dictionary-reference`)

## Scope and boundaries

This inventory records the permitted declaration/migration surface only. It is a first-pass
file-level classification; per-field decisions and the actual edits belong to T036/T037 (US5).

**Allowed roots** (explicit, non-exhaustive beyond these):

- `packages/aoa-action-machine` (src + tests + tests/support)
- `packages/aoa-maxitor` (src + tests + client)
- `packages/aoa-fastapi-adapter`, `packages/aoa-langgraph`, `packages/aoa-mcp-adapter`,
  `packages/aoa-ocel`, `packages/aoa-otel` (other non-excluded packages)
- `tests` (top-level)
- `scripts`
- `examples`

**Excluded (never read/searched/executed/modified)**:

- `packages/aoa-demo` and any `demo` subtree
- `*_draft.md`, `*.ru_draft.md`, `*.ru.md` (including root `README.ru_draft.md`)
- `scripts/run_checks_with_log.sh` (aggregate check script; forbidden as a command, listed
  here only as a named exclusion)

No forbidden path was opened during this inventory.

## Methodology

Commands run from the repository root against explicit allowed roots, each piped through
`grep -v "/aoa-demo/"`. Summary of the scans:

| Scan | Pattern | Result |
| --- | --- | --- |
| NoRelation usage | `NoRelation` | 57 lines / 19 files |
| Inverse usage | `Inverse\(` | 272 lines / 67 files |
| Relation containers | `AssociationOne[…], …, Generalization[…], Specialization[…]` | 382 lines |
| Bare dictionary field | `field: *Enum* = Field` (incl. `\| None`) | 50 fields / 24 files |

## A. Bare / nullable dictionary fields — must become `AssociationOne[D]`

The old accepted form is `currency: CurrencyEnumEntity = Field(...)` (required) or
`currency: CurrencyEnumEntity | None = Field(default=None, ...)` (optional). This feature
replaces both with `Annotated[AssociationOne[D] | None, NoInverse()]`.

**Test fixtures** (migration in T037, plus subprocess isolation in T003 where the fixture is
an intentionally-invalid declaration):

- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`
  — 14 bare dictionary fields across the refusal fixtures (lines 210–214, 347, 363, 372, 381,
  390, 398, 414, 476). These are intentionally-invalid/control fixtures and are also in scope
  for T003 isolation.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py`
  — `currency`, `settlement_currency` (lines 122–123).
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`
  — 13 bare dictionary fields (lines 70–71, 80, 89, 98, 107, 124, 188, 205, 232–233).
- `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py`
  — `currency`, `settlement_currency` (lines 74–75).

**Teaching examples** (migration + execution in C2/T040):

- `examples/step_20_dictionaries/*.py` — 20 files each declare a bare
  `currency: CurrencyEnumEntity = Field(...)`:
  `01_reference_field`, `02_reference_payload`, `03_serialization`, `04_storage_mapping`,
  `05_optional` (adds `| None`), `06_inheritance`, `07_frozen`, `08_graph`, `09_erd`,
  `20_bare_code`, `21_unknown_code`, `22_copy`, `23_missing_code`, `24_blank_reference`,
  `25_flat_fields`, `26_duplicate_code`, `27_blank_code`, `28_blank_label`,
  `29_empty_dictionary`, `53_dictionary_catalogues`.
- `examples/step_20_entity/07_enumeration.py` — declares `CurrencyEnumEntity` catalogue
  directly (no entity host field); review whether its catalogue usage needs the new wrapper
  or remains a standalone dictionary API control.

**Schema-mechanics tests to review (not plain entity hosts)**: the dictionary core/json-schema
tests exercise the standalone dictionary schema API, which the specification keeps unchanged;
they are listed in T037 as positive fixtures to migrate only where they are entity hosts.
Fields like `rated: SchemaRatedEnumEntity` (no `= Field`) in
`test_dictionary_json_schema.py` are plain Pydantic models, not relationship hosts — verify
against the resolved host stereotype during T037 rather than migrating blindly.

## B. NoRelation fields — embedded-value alternative must be removed

`NoRelation("reason")` is the formerly accepted embedded-entity alternative that this feature
refuses. The marker class and its check are also part of the public API that must stop
accepting embedded declarations.

**Library source** (the marker and its enforcement):

- `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py`
  — `NoRelation` class definition (lines 233–286). Keep the class (it must produce refusals),
  change its acceptance path.
- `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py`
  — re-export.
- `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`
  — `_check_marker` accepts `NoRelation` as a legal embedded form (lines 368–392); this must
  refuse instead (T011).

**Test fixtures**:

- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`
  — `StateMarkerCoreEntity`, `MarkerOnEnumCoreEntity`, `MarkerWithRelationCoreEntity`,
  `EmbeddedCoreEntity` (the currently-legal embedded form, lines 459–466) and the related tests.
- `packages/aoa-action-machine/tests/action_machine/smoke/test_lazy_exports_coverage.py`
  — likely asserts the marker is exported; review.

**Teaching examples** (`examples/step_21_relations/`, all mention `NoRelation` in refusal or
embedded-value scenarios):

- `54_embedded_entity.py` — the primary embedded-value scenario (must be rewritten to a
  supported relationship or removed from the "legal" set).
- `55_bare_entity_refused.py`, `52_required_relation.py`, `53_optional_relation.py`,
  `56_relation_description.py`, `57_relation_factory.py`, `58_relation_null_default.py`,
  `59_relation_object_default.py`, `60_entity_collection.py`, `61_marker_on_relation.py`,
  `62_marker_on_scalar.py`, `63_conflicting_markers.py`, `64_nullable_required_relation.py`
  — refusal/diagnostic examples that name `NoRelation` in messages; text updates required.
- `examples/step_20_dictionaries/50_dictionary_declarations.py` — dictionary declarations
  referencing the marker; update the described contract.

## C. Missing / one-sided inverse markers

The new contract requires both endpoints of a reciprocal pair to declare `Inverse`, and
`NoInverse()` only for genuinely one-way fields. This scan cannot decide reciprocity at the
file level; the following files contain `Inverse(` or direction markers and must be audited
pair-by-pair in T014 (inverse validator tests) and migrated in T036:

**Test support / fixtures**:

- `packages/aoa-action-machine/tests/support/domain_model/entities.py`
  — `RelatedCoreEntity` and `ComplexCoreEntity` use `NoInverse()` (explicitly unpaired,
  retained); no reciprocal `Inverse` pair here, so no one-sided defect, but the nullable
  `AssociationOne[...] | None` + `NoInverse()` forms must stay complete declarations.
- `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_sweep.py`,
  `test_entity_specialization_rules_axis.py`, `test_entity_specialization_graph.py`,
  `test_graph_json_schema_specialization.py` — specialization head/alternative `Inverse`
  usage (dedicated contract; heads name only the partner field).
- `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_specialization_resolver.py`,
  `test_entity_intent_resolver.py` — resolver-level `Inverse` fixtures.
- `packages/aoa-action-machine/tests/action_machine/domain/test_entity_introspection.py`,
  `test_relation_markers.py` — marker introspection fixtures.

**Other packages**:

- `packages/aoa-ocel/tests/plugin/test_ocel_plugin.py` — `AssociationOne[PolicyCoreEntity] | None` + `NoInverse()` (unpaired, retained).
- `packages/aoa-ocel/examples/01_ocel_export.py` — `AssociationOne[CustomerCoreEntity] | None` + `NoInverse()` (unpaired, retained).

**Teaching examples** (reciprocity must be checked per pair):

- `examples/domain_model/01_domain_model.py`
- `examples/step_20_entity/04_association.py`, `05_detail.py`, `06_specialization.py`
- `examples/step_21_relations/*` (many `Inverse` scenarios; the `30_error_no_reverse.py`,
  `31_error_two_reverse_fields.py`, `29_error_inverse_name.py` files already target inverse
  diagnostics and must be reconciled with the reciprocal contract)
- `examples/step_26_maxitor/01_graph.py`

## D. Affected value construction

The dictionary runtime contract changes how host fields hold values: a bare member is no
longer accepted; an explicit `AssociationOne[D](id=..., entity=...)` wrapper is required.

- `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py`
  — `BaseRelationOne`/`BaseRelationMany` constructors; dictionary handling is added in T025.
- `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`
  — canonical `by_code` lookup reused by the new wrapper (T025).
- Test/example construction of dictionary host values: the bare `CurrencyEnumEntity.EUR`
  assignments in the files listed under §A, and `AssociationOne(id=...)` constructions in the
  relation-container tests and `examples/step_20_dictionaries` / `examples/step_21_relations`.

## Boundary note

The only production (`*/src`) entity declaration with entity-valued fields is
`packages/aoa-maxitor/src/aoa/maxitor/model/core/entities/node_entity.py`, and it uses only
scalar fields (`id`, `parent_id`, `label`, `type`, `ordinal`) — no dictionary, `NoRelation`
or `Inverse` surface. All other production sources are library/consumer code that does not
declare entity relationships. The migration surface is therefore concentrated in the test
corpus and teaching examples above, plus the library validator/resolver/graph code named in
the plan (W1–W4).
