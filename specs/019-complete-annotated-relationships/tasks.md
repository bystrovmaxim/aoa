# Tasks: Complete Annotated Relationships

**Branch**: `feature/issue-259-complete-annotated-relationships`
**Date**: 2026-10-24
**Input**: [Plan](plan.md), [specification](spec.md), [research](research.md), [data model](data-model.md), [validation guide](quickstart.md), and [contracts](contracts/complete-declarations.md).
**Tests**: Required by FR-018/019 and the specification's acceptance scenarios. Add focused regression tests before their corresponding implementation; record initial failures and restored passing outcomes.
**State**: Tasks generated only. Every checkbox is initially unchecked; the planning baseline is not implementation acceptance.

## Execution rules and path conventions

Paths below are repository-relative. New paths named in tasks are planned deliverables, not claims that those files already exist. Preserve current changes and staging; never commit, push, create a PR or merge without a separate explicit instruction. Do not change branches or edit the constitution.

The sections below are procedural groupings corresponding to the task template's setup/foundation/story/final stages, not repository commit phases. They do not authorize automatic commits. Any later authorized commit phases must obey the project's one-phase/one-commit rule.

Never read, search, execute or modify `packages/aoa-demo` or any `demo` subtree. Exclude `*_draft.md`, `*.ru_draft.md` and `*.ru.md` from all reads, searches, checks and edits. Use explicit allowed roots and audit transitive imports/tool configuration. The maintainer's exclusions override broad check/report defaults. Do not execute `scripts/run_checks_with_log.sh` or workspace aggregate tasks: they violate these boundaries.

`[P]` marks only tasks in the same ready batch that touch distinct files and have no incomplete dependency within that batch. It permits parallel work; it does not itself instruct spawning agents. Sequential implementation is valid. Tasks without `[P]` touching shared production modules must remain sequential.

No new ownership/container-pair matrix is authorized. Existing compatibility checks remain. Required changes are full declarations, reciprocal Inverse with NoInverse retained, and ordinary dictionary association edges.

## Procedure 1 — Setup and scoped evidence

**Purpose**: Establish the permitted corpus, reproduce the baseline and prepare test isolation without changing behavior.

- [x] T001 Inventory the permitted declaration/migration surface and import/check boundaries into `specs/019-complete-annotated-relationships/evidence/migration-inventory.md`, using explicit allowed roots under `packages/aoa-action-machine`, `packages/aoa-maxitor`, the other nonexcluded packages, `tests`, `scripts` and `examples`; classify bare/nullable dictionary fields, NoRelation fields, missing/one-sided inverse markers and affected value construction. Record actual paths and exclusions without inspecting forbidden paths.
- [x] T002 After T001, reproduce the six-file baseline command in `specs/019-complete-annotated-relationships/quickstart.md` with the existing `.venv` and importlib mode, audit its fixture imports, and record actual commands/results and dependency versions in `specs/019-complete-annotated-relationships/evidence/baseline.md`; do not assume the previous 107-test result is still current. Before production edits, also capture the selected existing compatibility/classifier controls and their actual outcomes in `specs/019-complete-annotated-relationships/evidence/compatibility-baseline.json`, with exact case inputs/paths, commands, baseline commit/source hashes and both endpoint orientations where relevant; use isolated probes when no existing test states a rule, and distinguish actually implemented checks from docstring claims. Do not derive baseline expectations from the removed matrix or from the later modified implementation.
- [x] T003 After T002, prepare isolated declared-model test execution in `packages/aoa-action-machine/tests/support/isolated_entity_models.py` and migrate intentionally invalid import-time declarations in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py` into that isolation; ensure the helper invokes fresh processes and does not use graph exclusion as a validation bypass or load forbidden package code.

## Procedure 2 — Foundational resolved-field and source-check support

**Purpose**: Supply a canonical metadata view shared by declaration, inverse and graph work. Complete T004–T007 before story implementation.

- [x] T004 [P] After T003, add descriptor/parser tests in `packages/aoa-action-machine/tests/action_machine/intents/entity/test_resolved_entity_fields.py` for completed FieldInfo annotation/metadata, explicit namespace rebuild, aliases/inherited fields, unresolved targets, nested/ambiguous unions and duplicate markers. Track effective_host separately from declaring_owner; verify unchanged inheritance retains endpoint identity while explicit overrides, MRO-selected declarations and target-changing generic substitutions receive the specified identity. Assert the data-model constraints “direction marker count is exactly one”, “description is nonblank” and “None only when declared; omission only with a permitted explicit default”. Confirm the new assertions fail before T006.
- [x] T005 [P] After T003, add source-check tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_source_check.py` for assignment-side single Field, forbidden annotation-side/duplicate Field, supported import aliases, unsupported relevant syntax and explicit-root exclusions; use isolated temporary source fixtures rather than source introspection as a runtime prerequisite. Confirm failures before T007.
- [x] T006 After T004, implement the build-local normalized descriptor in `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/resolved_entity_fields.py` and consume it from `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_relation_intent_resolver.py`; enforce “Resolved class identity; alternatives are allowed only by existing specialization grammar”, preserve all markers from FieldInfo, reject ambiguous shapes instead of selecting the first union member, and stop re-running get_type_hints against incomplete module globals. Preserve specialization's dedicated alternatives/vocabulary grammar and do not add a global registry.
- [x] T007 After T005 and T006, implement the explicit-root source checker in `scripts/check_complete_entity_fields.py`, covering the alias/forms from T005; reject/report unsupported relevant syntax instead of silently accepting it, enforce one assignment-side Field and exclusions, and verify T004/T005 pass. Runtime semantic checks must work without source files; do not claim FieldInfo preserves source spelling.

## Procedure 3 — US1: Declare every entity relationship explicitly (P1)

**Goal**: Core, Assoc, Detail, Spec and Enum have complete-declaration enforcement with no stereotype or presentation escape.
**Independent acceptance**: Each permitted owner/target stereotype has positive full declarations and refusals for every incomplete shape, with retained State/scalar controls. At this checkpoint, test the completeness slice independently; full inverse/runtime/export delivery follows in US2/US3.

### Tests first

- [x] T008 [P] [US1] After T007, extend `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py` with independently named Core, Assoc, Detail, Spec and Enum owner/target cases: full forms, nullable bare forms, collections/mappings, bare Annotated, NoRelation, missing/duplicate/conflicting direction markers, and description/default failures. Include valid Assoc endpoints, Detail ownership declarations, Spec alternatives and the explicit Enum single-association form. Assert exact error type/text and actual boundary; isolate invalid models and confirm red before T011.
- [x] T009 [P] [US1] After T007, add `packages/aoa-action-machine/tests/action_machine/graph/test_entity_declaration_entrypoints.py` covering hidden/excluded hosts, direct EntityGraphNode projection, coordinator/factory/machine construction and supported coordinator injection; assert invalid or unresolved declarations cannot publish a successful graph and that a previously validated coordinator remains usable. Confirm red before T012.
- [x] T010 [P] [US1] After T007, add `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_unchanged_controls.py` for scalar/schema fields, abstract framework kind bases, undeclared/unsupported entity targets, valid Lifecycle fields and existing bare-State refusals; preserve actual earlier declaration failures rather than moving every error to build time.

### Implementation and verification

- [x] T011 [US1] After T008/T010, update `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py` to enforce complete semantic declarations, reject bare Enum and NoRelation alternatives, count direction markers, retain current relation default discipline, and emit complete supported corrections. Enumerate all declared hosts for completeness including excluded hosts without widening specialization publication enumeration in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py`; never accept unresolved/unsupported entity-bearing types as scalar.
- [x] T012 [US1] After T009/T011, integrate completeness before publication in `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py`, `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` and the existing factory/machine injection paths as required by the supported contract in `packages/aoa-action-machine/src/aoa/action_machine/runtime/action_product_machine.py`; avoid graph-constructor recursion and do not remove supported validated-coordinator injection.
- [x] T013 [US1] After T011/T012, run T004–T010 and the relevant source gate using explicit permitted files, reconcile current source-check coverage with T001, and record exact positive/refusal results in `specs/019-complete-annotated-relationships/evidence/us1-completeness.md`; verify all five stereotypes independently, source spelling versus runtime semantics and no graph-exclusion escape. This is not the closing check run.

## Procedure 4 — US2: Declare reciprocal relationships across modules (P1)

**Goal**: Every mutual pair has explicit reciprocal Inverse markers; unpaired NoInverse remains supported. Cross-module models resolve without circular runtime imports.
**Independent acceptance**: Both import orders pass after explicit namespace rebuilding. Missing/wrong reverse targets, one-sided markers and Inverse targeting NoInverse fail before publication.

### Tests first

- [x] T014 [P] [US2] After T013, add `packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_validator.py` for field-only and explicit-class Inverse, class-identity mismatches (including same-named classes), absent/wrong reverse fields, nonreciprocal pairs, NoInverse as an invalid claimed reverse, valid one-way controls, cycles and the intentionally breaking one-sided migration. Include Base.items / Item.owner with unchanged Child inheritance, explicit override with a new valid pair, override incorrectly pointing to the base pair, inherited override on a grandchild, diamond/MRO selection, same-named unrelated declarations and target-changing generic substitution; preserve per-effective-host projection. Assert exact diagnostics and confirm red before T017.
- [x] T015 [P] [US2] After T013, add isolated two-module fixtures under `packages/aoa-action-machine/tests/support/complete_relationships/{offer,region,bootstrap}.py` and `packages/aoa-action-machine/tests/action_machine/graph/test_entity_inverse_cross_module.py`; use postponed annotations, type-checking imports and explicit rebuild namespaces. Verify both import orders in fresh processes plus unresolved-name failure, with no dependency on repeated get_type_hints.

### Implementation and verification

- [x] T016 [US2] After T014/T015, extend field-only marker resolution and explicit-target identity checking in `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_relation_intent_resolver.py` and update the public marker contract in `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py`; infer the target from the completed container, retain concrete-class markers, retain NoInverse and introduce no string class target API.
- [x] T017 [US2] After T016, implement build-local reciprocal endpoint checks in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_inverse_validator.py`, using `(declaring_owner_class_identity, field_name)` keys and descriptor inspection; resolve effective fields to canonical declaring endpoints on both sides and require the reverse marker to return to that same endpoint. Preserve completeness checks and graph sources per effective host, distinguish explicit/semantic overrides, and do not substitute blanket issubclass matching for explicit marker-target identity. Do not recurse through graph node creation or introduce any ownership/container-pair matrix.
- [x] T018 [US2] After T017, integrate reciprocal checks for specialization heads and every alternative in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py` and focused tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py`; retain existing classifier membership/coverage and treat vocabulary parameters as vocabulary rather than extra relationship fields.
- [x] T019 [US2] After T018, wire inverse checks into `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py` and supported direct projection in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py`; extend `packages/aoa-action-machine/tests/action_machine/graph/test_entity_declaration_entrypoints.py` to prove the same inverse guarantee across supported publication/injection paths without changing graph publication exclusions.
- [x] T020 [US2] After T019, execute the US2 tests, relevant marker tests in `packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py` and US1 controls; record real both-import-order, one-way and reciprocal migration outcomes in `specs/019-complete-annotated-relationships/evidence/us2-inverse.md`. Fix failures before proceeding; keep NoInverse behavior explicit.

## Procedure 5 — US3: Select and export a dictionary value explicitly (P1)

**Goal**: Explicit dictionary containers canonicalize safely and export the prescribed reference JSON and ordinary association graph.
**Independent acceptance**: Python wrapper input and JSON id-container input normalize to the canonical member, invalid values fail, both schema modes resolve, and graph/diagram output has one ordinary association plus the retained field hint.

### Tests first

- [x] T021 [P] [US3] After T020, add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association.py` for id-only wrappers, identity-matching supplied members, unknown/wrong-type ids, copies/foreign/mismatched members, forbidden raw member/code/reference/Python mapping inputs, required/nullable/default boundaries, and unchanged structural wrappers. Assert “The validated field receives a new immutable wrapper with canonical entity and matching id” and “No input wrapper is mutated”; confirm red before T025.
- [x] T022 [P] [US3] After T020, add `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association_schema.py` for JSON-only `{id: string}` input (no extra keys), rejection of old reference JSON, matching Python-mapping refusal, JSON output equal to to_reference(), nullability, custom field serializers and handler-resolved enum/date definitions in standalone/containing schemas. Assert `field.entity is D.by_code(field.id)` after host validation and keep validation/output asymmetry explicit.
- [x] T023 [P] [US3] After T020, add `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_association_graph.py` for one ordinary entity_relation edge, exact ordinary properties, required/nullable shape stability, omitted inverse identifiers, deprecation metadata, one retained entity_field row, reference_qualname identity, inherited per-host field/edge identity, NoGraphEdge presentation controls and no new special/duplicate edges; retain ordinary structural row behavior as a neighboring control.
- [ ] T024 [P] [US3] After T020, extend `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py` with new ordinary association fixtures: association relationship_kind, source/target multiplicities zero_many/one, dictionary catalogue/type hint preservation, cross-domain/neighbour slicing and no duplicate arrow candidates. Assert exactly one fields item per dictionary host/field, preserve retained field_id/type/ordinal/reference_qualname, enrich foreign_key=true from the matching ordinary edge, and reject a second synthesized FK row. Include two fields to the same dictionary plus unchanged ordinary structural fallback and NoGraphEdge controls. Keep historical reference-edge import controls separately named and verify red before T029.

### Implementation and verification

- [x] T025 [US3] After T021/T022, add Pydantic generic core/JSON-schema handling scoped to AssociationOne[D] in `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py`, reusing canonical dictionary lookup and handler-managed serialization from `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py`. Python requires an explicit wrapper; JSON accepts only the explicit id object; reject unknown/foreign/fabricated/mismatched values, normalize into a new frozen wrapper, serialize JSON to the existing member reference and leave ordinary structural container behavior unchanged.
- [x] T026 [US3] After T025, finish the strict dictionary declaration branch and exact corrections in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`: only AssociationOne[D] or its nullable form with NoInverse is legal; require a concrete nonempty available dictionary target and refuse dictionary Inverse, unsupported containers and bare forms. Preserve standalone dictionary catalogue/reference APIs.
- [x] T027 [US3] After T023/T026, extend dictionary target detection in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_field_graph_node.py` and retained-row selection in `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py`; emit exactly one dictionary field row whose reference_qualname equals the ordinary relation target, without returning scalar rows for unrelated structural relations.
- [x] T028 [US3] After T027, route dictionary relationships solely through ordinary `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_graph_edge.py` projection and retire new-source special-reference gathering in `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py` and `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_reference_graph_edge.py`. Migrate current-generation assertions in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py` and `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py`; retain historical entity_reference schema/import controls in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py` rather than deleting legacy support.
- [ ] T029 [US3] After T024/T028, integrate the new graph projection with `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py` and `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`, preserving ordinary association handling and legacy imports; adjust source only where needed and migrate fixtures/snapshots in `packages/aoa-maxitor/tests/test_full_graph_payload_shape.py` and T024. Identify dictionary targets by stereotype; never synthesize a second relation from reference_qualname. Join/enrich dictionary field rows with ordinary association FK metadata by `(entity_id, field_name)` and target identity, suppress the matching synthesized FK fallback before aggregation, and retain field identity/type/order/hint. Keep ordinary structural fallback, historical inputs and slice-specific arrow visibility; full-row DISTINCT is not sufficient.
- [ ] T030 [US3] After T029, migrate and extend `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` to verify the new association payload keeps the dictionary card/type hint and renders one arrow; run with a compatible existing Node runtime/runner. Preserve dedicated historical payload cases; do not introduce a new renderer path if the existing association path already satisfies the contract.
- [x] T031 [US3] After T030, run the runtime/schema/graph/payload/renderer partitions, validate exact ordinary edge JSON against the existing relation schema, and record actual Python input, JSON input/output and consumer results in `specs/019-complete-annotated-relationships/evidence/us3-dictionary.md`; include standalone dictionary and ordinary relation-container controls, single merged payload rows, distinct same-dictionary fields and structural FK fallback controls, and do not claim direct output-to-input round-tripping.

## Procedure 6 — US4: Preserve existing compatibility (P2)

**Goal**: The full-form/inverse/dictionary changes add no independent ownership matrix or runtime uniqueness/cascade policy.
**Independent acceptance**: Complete declarations retain existing compatibility/classifier outcomes except for the explicitly specified feature changes; both endpoint orientations are controlled where relevant.

- [x] T032 [US4] After T031, add `packages/aoa-action-machine/tests/action_machine/graph/test_relationship_compatibility_regressions.py` using the pre-change cases/results in `specs/019-complete-annotated-relationships/evidence/compatibility-baseline.json` from T002 and the inventory to distinguish actually existing checks from source-docstring claims; compare against those recorded outcomes rather than deriving expected results from the changed code; cover permitted neighboring complete declarations and existing refusals, including composite/aggregate/association and specialization controls plus the accepted unchanged-inheritance behavior, without deriving expected refusal from the removed matrix.
- [x] T033 [US4] After T032, review changes to `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`, `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_inverse_validator.py` and `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py`; remove any accidentally introduced ownership/container-pair policy while retaining the new required declaration/reciprocity/dictionary checks and existing compatibility failures. Do not add instance uniqueness, storage constraints or cascades.
- [x] T034 [US4] After T033, run the compatibility, classifier and State/Lifecycle controls and record exact unchanged/intentional-change classifications in `specs/019-complete-annotated-relationships/evidence/us4-compatibility.md`; check that no acceptance/refusal is justified only by the discarded matrix.

## Procedure 7 — US5: Migrate existing declarations (P2)

**Goal**: Authorized existing models/fixtures use the complete form and explicit values; migration failures explain the intentional breaking changes.
**Independent acceptance**: Old bare dictionary, NoRelation and one-sided forms fail with actionable corrections; replacements pass, and the permitted corpus contains no remaining unsupported declarations.

- [x] T035 [US5] After T034, add isolated before/after migration regressions in `packages/aoa-action-machine/tests/action_machine/graph/test_complete_relationship_migration.py`: bare/nullable dictionary to explicit association+container, NoRelation to a complete supported relationship, and one-sided inverse to reciprocal markers. Assert actual exception text and replacement results; preserve standalone dictionary APIs and existing compatibility boundaries.
- [x] T036 [US5] After T035, migrate production declarations and value construction identified in `specs/019-complete-annotated-relationships/evidence/migration-inventory.md` under explicit nonexcluded package source roots, including `packages/aoa-maxitor/src/aoa/maxitor/model`; complete reciprocal fields and required/nullable dictionary wrappers together, preserving codes and runtime intent. Update the inventory with each exact source path and disposition; do not inspect/migrate excluded packages to get green.
- [ ] T037 [US5] After T036, migrate positive fixtures and supported construction paths in `packages/aoa-action-machine/tests/support/domain_model`, `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_core_schema.py`, `packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_json_schema.py`, affected `packages/aoa-action-machine/tests/action_machine/graph` fixtures and `packages/aoa-maxitor/tests`; keep direct dictionary tests separate from entity-field migration and keep intentionally invalid declarations subprocess-isolated.
- [ ] T038 [US5] After T037, run before/after regressions and audit the permitted source/test inventory with `scripts/check_complete_entity_fields.py`; record remaining exclusions, each supported migration outcome and any reproduced source defect in `specs/019-complete-annotated-relationships/evidence/us5-migration.md`. Mark source/test migration complete only when no authorized production/test declaration relies on a bare target, NoRelation alternative or implicit reverse marker. Teaching-material migration and execution remain in C2 below.

## Procedure 8 — Final cross-cutting tail: exactly three tasks

All behavior and authorized production/test migrations must be settled first. These three tasks are sequential and may not be absorbed into earlier tasks. Do not append another implementation/check task after the changelog.

- [ ] T039 Complete **C1 — scoped closing check run to zero** after T038: follow audited commands in `specs/019-complete-annotated-relationships/quickstart.md`, run permitted tests/lint/format/type checks, applicable client/build/packaging checks and the scoped source gate on migrated production/positive-test roots (teaching-source migration and its gate belong to C2); resolve every in-scope failure. In isolated copies/processes separately restore bare Enum acceptance, NoRelation, missing-marker acceptance, nonreciprocal acceptance and special dictionary-edge generation; require each targeted regression to fail and valid neighboring controls to pass, then verify production source/index unchanged by mutations. Record exact commands, outputs, mutation controls, unavailable/excluded coverage and remaining reproduced defects in `specs/019-complete-annotated-relationships/evidence/closing-checks.md`; never run the forbidden aggregate check script or claim a full-repository pass.
- [ ] T040 Complete **C2 — English documentation and executed teaching scenarios** only after T039: update `docs/how-to/explicit-entity-fields.md`, `docs/how-to/dictionary-references.md`, `docs/how-to/dictionary-validation-and-export.md`, `docs/reference/intents-and-invariants.md`, `docs/tutorials/step-20-dictionaries.md` and `docs/tutorials/step-26-maxitor.md` plus affected authorized pages from the inventory. Migrate affected paired scripts/notebooks in `examples/step_20_dictionaries` and `examples/step_21_relations`, including `08_graph.py/.ipynb`, `09_erd.py/.ipynb`, `50_dictionary_declarations.py/.ipynb`, `53_dictionary_catalogues.py/.ipynb` and `55_refusal_diagnostics.py/.ipynb`; preserve existing numbering and place any new grouped scenario after the actual highest number. Include complete examples for all stereotypes and a two-module inverse scenario with composition root. Each script has main(), a topic/run-command docstring, exact expected-error assertions and actual output; notebooks use matching declarations/calls/checks with explanatory cells, real outputs and execution counts. Execute every changed script/notebook in a fresh environment, compare outputs, run standalone documentation blocks and the source gate on migrated teaching roots, validate links/anchors, remove stale claims/links and record execution mode/results in `specs/019-complete-annotated-relationships/evidence/documentation-execution.md`. A failing example blocks this task; any required behavior repair invalidates C1 and requires repeating T039 before finishing C2.
- [ ] T041 Complete **C3 — changelog last** only after T040: update `docs/CHANGELOG.md` with one dated human-readable article (2–5 short paragraphs, migration/refusals, issue link at the end) and bold-leading behavior entries in `packages/aoa-action-machine/CHANGELOG.md` and `packages/aoa-maxitor/CHANGELOG.md` following their categories. Refine existing entries rather than duplicate them; update no behavior-unchanged or excluded package. Preserve historical context and ensure no current limitation/entry claims bare dictionary acceptance, a new ownership matrix or newly emitted special reference edges. Confirm all recorded evidence is accurate and report changes/examples/limits without committing or staging.

## Story and task dependencies

| Group | Tasks | Prerequisite / completion boundary |
| --- | --- | --- |
| Setup | T001–T003 | Current branch and scope; no earlier task needed for T001 |
| Foundation | T004–T007 | T003; T004/T005 independent; T006 follows T004; T007 joins T005/T006 |
| US1 (P1) | T008–T013 | T007; T008/T009/T010 independent; T011 joins shape/unchanged tests; T012 joins entry-point tests and implementation; T013 verifies |
| US2 (P1) | T014–T020 | T013; T014/T015 independent; T016–T020 sequential |
| US3 (P1) | T021–T031 | T020; T021/T022/T023/T024 independent; T025 joins runtime/schema tests; T026–T031 sequential, joining graph/consumer tests where stated |
| US4 (P2) | T032–T034 | T031; sequential compatibility audit/control slice |
| US5 (P2) | T035–T038 | T034; tests → production → fixtures → inventory completion |
| Closing | T039–T041 | T038 → C1 → C2 → C3 |

```text
Setup → Foundation → US1 → US2 → US3 → US4 → US5 → C1 → C2 → C3
```

Test isolation/support updates discovered while implementing a story are prerequisites for that story's focused execution; do not defer a required positive control's migration just because broad corpus migration is grouped under US5. Global loaded-class checks may require migrating the affected permitted support fixtures early. Record such file moves in the inventory while retaining their story ownership; never disable the completeness gate to keep a fixture alive.

Cross-story dependencies are real: a complete Enum declaration can be validated for shape in US1 before its new runtime/schema/export behavior is delivered in US3. Do not label US1 alone a completed or releasable implementation of the universal requirement.

## Parallel execution examples

| Story | Safe ready batch | Shared-file constraint |
| --- | --- | --- |
| US1 | After T007, T008 validator tests, T009 entry-point tests and T010 unchanged-control tests can be authored independently. | T011/T012 production integration stays sequential. |
| US2 | After T013, T014 inverse validator tests and T015 isolated cross-module fixtures/tests can be authored independently. | Shared resolver, coordinator and specialization edits T016–T019 stay sequential. |
| US3 | After T020, T021 runtime tests, T022 schema tests, T023 graph tests and T024 Maxitor payload tests can be authored independently. | T025–T031 touch shared declaration/projection paths and follow listed dependencies. |
| US4 | No intra-story parallel batch: T032 defines controls before T033 audit/fixes and T034 verification. | Do not run a separate compatibility implementation in parallel with inverse changes. |
| US5 | No intra-story parallel batch by default: inventory-driven source/fixture migrations can overlap files and require shared values. | Split only after T001 identifies disjoint paths and all prerequisite behavior is ready. |

Foundation's T004/T005 are also independent after T003. Closing tasks are never parallel. An independent test-authoring batch does not mean multiple pytest processes can share mutable fixture/model state; execute isolated suites appropriately.

## Requirement coverage

| Requirements | Tasks / acceptance evidence |
| --- | --- |
| FR-001 | T004–T013, T039, T040: source placement and normalized runtime semantics |
| FR-002–007 | T008, T010, T011, T021, T026, T040: each stereotype independently, State/scalar controls |
| FR-008 | T004, T006, T014–T016, T020: field-only and explicit targets, both import orders |
| FR-009 | T014, T017–T020, T035–T037: reciprocal markers, NoInverse retained, migration |
| FR-010 | T032–T034, T039: preserved checks and absence of a new ownership matrix |
| FR-011–012 | T021, T025, T026, T031: explicit wrappers, canonical identity and nullable/default limits |
| FR-013 | T022, T025, T031: JSON container branch, reference output and resolved schemas |
| FR-014 | T023, T024, T027–T031: ordinary edge, retained hint, legacy input and consumer projection |
| FR-015 | T003, T009, T012, T015, T019, T039: isolation, excluded hosts, publication paths and unresolved failures |
| FR-016 | T008, T011, T014, T017, T026, T035: exact meaningful refusals and corrections |
| FR-017 | T035–T038, T040, T041: explicit migration and breaking changes |
| FR-018 | T008, T010, T015, T040: stereotype-specific acceptance and executed teaching scenarios |
| FR-019 | T039 using focused story regressions: all five mutations and valid neighbors |
| FR-020 | T039, T040, T041 only: exactly three ordered closing tasks |

SC-001/002 map to US1 and publication controls; SC-003 to US2; SC-004 to US4; SC-005 to US3; SC-006 to US5 plus C2; SC-007 to C1; SC-008 to T010/US4/C1. Data-model constraints are quoted in T004/T021 and implemented through T006/T011/T025; projection identity and nonduplication are checked by T023/T027–T031.

## Implementation strategy and checkpoints

1. Complete scoped setup and foundation without dependency upgrades or unrelated refactoring.
2. Implement and verify US1 as the first development slice. This is a completeness checkpoint, not feature completion or permission to ship.
3. Complete US2 and US3 for the minimum coherent P1 increment: complete declarations, reciprocal inverse handling and explicit dictionary runtime/export. Validate each story with isolated controls.
4. Complete US4/US5 to demonstrate existing compatibility preservation and migrate the authorized real corpus. No story checkpoint waives these delivery requirements.
5. Finish the three closing tasks in order. The finished feature requires every task, not just the P1 increment. A source behavior change during documentation sends verification back to C1.

All implementation tasks remain unchecked until actually performed. Baseline evidence, generated design documents and a passing requirements-quality checklist do not mark implementation tasks complete. No code implementation, deployment or publication action is authorized by generating this file.
