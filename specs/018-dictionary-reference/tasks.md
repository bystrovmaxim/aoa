# Tasks: a dictionary-typed field is a declared reference, and the graph carries it as an edge

**Feature**: `specs/018-dictionary-reference` | **Branch**: `feature/issue-256-dictionary-reference` | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

**Input**: Design documents from `specs/018-dictionary-reference/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (`US1`–`US4`, mapped to spec.md)
- Every task names the file it touches; a task that does not name one is not a task

## Path Conventions

Repository root is the working directory. Python packages live under `packages/*/src/aoa/*`,
their tests under `packages/*/tests/`, the viewer under `packages/aoa-maxitor` (Python action)
and `packages/aoa-maxitor/client` (TypeScript), examples under `examples/`, pages under `docs/`.

## Phase order

The phase order below is the plan's commit order, which is also the story order: the rule must
exist before an edge can be emitted, and the edge must exist before the ERD can draw it. The
diagnostics phase is independent of all three and comes last among the work items.

| Tasks phase | Plan phase | Story | Priority |
| --- | --- | --- | --- |
| 1. Setup | — | — | — |
| 2. US1 | 1 | the dictionary kind enters the rule | P1 |
| 3. US2 | 2 | the graph carries the reference | P1 |
| 4. US3 | 3 | the ERD shows the reference | P2 |
| 5. US4 | 4 | a refusal names the shape | P3 |
| 6. Polish | 5–7 | check run, documentation, changelog | — |

---

## Phase 1: Setup

- [x] T001 Re-run `specs/018-dictionary-reference/evidence/baseline_probe.py` and paste its exact output into the "Measured baseline" section of `specs/018-dictionary-reference/research.md`, replacing any paraphrase (FR-031; SC-002)
- [x] T002 Refresh the dictionary-field counts over `packages/`, `examples/` and `tests/` (baseline 60: 26 demo, 23 examples, 11 tests) and update "Scale/Scope" in `specs/018-dictionary-reference/plan.md`, SC-002 and FR-031 in `specs/018-dictionary-reference/spec.md` when a count moved (FR-031; SC-002)

---

## Phase 2: User Story 1 — a dictionary-typed field is judged by the entity-field rule (Priority: P1) 🎯 MVP

**Goal**: the bare dictionary type and its optional form are accepted as the declared reference; a collection of dictionary values, a relation container around a dictionary, `NoRelation` on a dictionary, an empty catalogue and a reference to a dictionary outside the graph are refused at the declaration boundary, each with a message that names the field and the form that fits.

**Independent test**: declare one isolated model per row of `contracts/dictionary-reference-field.md` and read the answers; a model with an accepted form builds, a model with a refused form fails at the declaration boundary before any graph is wired.

### Tests for User Story 1

- [x] T003 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `D` and `D | None` are accepted and produce no refusal; a reference acquires no relation default rule — `D = Field(default=None)` on a non-nullable annotation is not refused by this change, and `D = Field(default_factory=…)` is not refused either (FR-001, FR-002, FR-032; SC-001)
- [x] T004 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `tuple[D, ...]`, `list[D]`, `Sequence[D]`, `set[D]`, `frozenset[D]` and `dict[str, D]` are refused, and the message names `D`, `D | None` and never `AssociationMany` (FR-003; SC-001)
- [x] T005 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `AssociationOne`/`Many`, `CompositeOne`/`Many`, `AggregateOne`/`Many` and `Generalization` around a dictionary are refused with a message stating that a shared value is not an association target; `Specialization[A | B, D]` stays legal (FR-004; SC-001)
- [x] T006 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `Annotated[D, NoRelation("…")]` is refused and the message says the bare dictionary type already declares the reference (FR-005; SC-001)
- [x] T007 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: an empty catalogue is refused in every form, bare, optional and collection, at the declaration boundary; a dictionary that is not a graph model (undecorated or `exclude_graph_model`) is refused naming the field and the dictionary; a dictionary that is both empty and outside the graph reports the empty catalogue first (FR-006, FR-014; SC-001)
- [x] T008 [P] [US1] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: the kind classifier reports `Enum` for a dictionary and never `Core`/`Assoc`/`Detail`/`Spec`/`State`; an inherited dictionary field and a forward-referenced one are judged after resolution; an `Annotated` form is judged on its inner type; an excluded host is not judged; a dictionary reference on a `Spec`, `Assoc` and `Detail` host is judged exactly as on a `Core` host (FR-007, FR-008, FR-009, FR-016)

### Implementation for User Story 1

- [x] T009 [US1] Turn `_STRUCTURAL_BASES` into `_ENTITY_BASES` with `(BaseEnumEntity, "Enum")` and return `"Enum"` from `_kind_of` in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`, updating the module header's RULES section and the function's AI-CORE block (FR-001, FR-009)
- [x] T010 [US1] Add the dictionary branches to `_check_relation`, `_check_marker` and `_check_field` in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`: accept the bare and optional reference, refuse a collection, a container and the marker, and write the three messages with the owner, the field, the resolved type and the two accepted forms (FR-002, FR-003, FR-004, FR-005)
- [x] T011 [US1] Move the empty-catalogue check into the validator and delete `_refuse_empty_dictionary` from `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py`; add the not-a-graph-model check (`entity_info_is_set` and not `excluded_from_graph_model`) beside it in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`; move `test_a_field_typed_by_an_empty_dictionary_is_refused` from `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py` to the validator test, so it fails at the boundary that now owns the rule (FR-006, FR-014)
- [x] T012 [US1] Run `quickstart.md` proofs 1–6 against the branch and record each answer in `specs/018-dictionary-reference/quickstart.md`; confirm the 49 non-test corpus fields (26 demo, 23 examples) still build and the collection shape of proof 2 is refused; the reporting model is its owner's acceptance against this build, not a run this task can take (SC-002, SC-003)
- [x] T013 [US1] Adversarially restore the enum exclusion (drop the `BaseEnumEntity` branch from `_kind_of`), confirm T004 (all five collection cases) and T008 (the classifier) fail while the structural-entity control still passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`) (FR-027; SC-007)

**Checkpoint**: the form table passes case by case, the corpus builds, and the two reporting-model collections are refused with the form that works.

---

## Phase 3: User Story 2 — the graph carries the reference as an edge (Priority: P1)

**Goal**: every accepted dictionary reference produces one typed `entity_reference` edge to the dictionary, the field row keeps `reference_qualname`, the graph schema declares the edge, and a reference to a dictionary outside the graph is refused before referential integrity can report a dangling target.

**Independent test**: build the reproducer graph, walk its edges and find the reference edge with the field name; validate the document against `GRAPH_JSON_SCHEMA`; confirm the row and the edge name the same dictionary; confirm an excluded dictionary is refused by the rule, not by `InvalidGraphError`.

### Tests for User Story 2

- [x] T014 [P] [US2] Add `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`: one `entity_reference` edge per accepted reference, with `field_name`, `cardinality` `one` and the dictionary as target; the edge count equals the accepted reference count; the reproducer shape is a checked regression — `region` accepted with an edge, `regions` refused with the collection message, and no dictionary-typed field passes the rule unjudged (FR-010, FR-028; SC-004)
- [x] T015 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`: the field row carries `reference_qualname` naming the same dictionary the edge targets; an inherited reference, a forward-referenced one and one on a `Spec`, `Assoc` and `Detail` host produce the edge; a reference and a specialization axis naming the same dictionary keep both edges distinct; two same-short-name dictionaries keep separate targets (FR-011, FR-012, FR-015, FR-016)
- [x] T016 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`: the document including the reference edge validates against `GRAPH_JSON_SCHEMA`; a graph without the `$defs` entry is refused (FR-013; SC-004)
- [x] T017 [P] [US2] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py`: a field referencing a dictionary marked `exclude_graph_model` is refused by `validate_entity_fields()` with a message naming the field and the dictionary, and the build never reports a dangling target (FR-014)

### Implementation for User Story 2

- [x] T018 [US2] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_reference_graph_edge.py` — module header, `AssociationGraphEdge` base, `edge_name` `entity_reference`, properties `field_name` and `cardinality`, `to_dict()` with `source_id`, a static builder reading the accepted dictionary fields, AI-CORE block and one-line docstrings (FR-010)
- [x] T019 [US2] Add `references` to `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py`: build them in `__init__`, return them from `get_all_edges()`, and extend the class CONTRACT (FR-010, FR-016)
- [x] T020 [US2] Declare the edge in `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py` — a `$defs/entity_reference` entry over `link_row` with `field_name` and `cardinality` required, added to `link.oneOf` (FR-013)
- [x] T021 [US2] Move `validate_entity_fields()` to the start of `NodeGraphCoordinator.build()` in `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py`, ahead of `_gather_all_nodes`, so a refused target is named before the wiring pass, and state the new order in the method's docstring and the class contract (FR-014)
- [x] T022 [US2] Register the edge in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`: a `CREATE TABLE entity_reference_edges (source_id, target_id, relationship, is_dag, field_name, cardinality)`, `_fill_table_entity_reference_edges`, the union-view entry, the edge-type list and the `known_edges` set, and the install dispatch; extend `packages/aoa-demo/tests/test_demo_dictionary_graph.py` with the build assertion — the demo graph loads through `DuckDBGraphResource` with the new type (FR-013; the resource raises `KeyError` on an unknown type)
- [x] T023 [US2] Update the `BaseEnumEntity` AI-CORE block and docstring in `packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py` to state that a field typed by the dictionary produces a reference edge (FR-010)
- [x] T024 [US2] Adversarially drop the references from `EntityGraphNode.get_all_edges()`, confirm T014 fails while the field-row assertion in T015 still passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py`) (FR-027; SC-007)

**Checkpoint**: the reference is reachable by walking edges, the document validates, the demo graph still loads into DuckDB, and no dangling target can be produced.

---

## Phase 4: User Story 3 — the ERD shows the reference (Priority: P2)

**Goal**: the slice payload carries one `reference` relation per accepted field, the arrow reaches the dictionary card, a dictionary in another domain joins the slice when neighbours are requested, and the dictionary card keeps #249's behaviour.

**Independent test**: produce the payload and the SVG for a domain with a host and its dictionary, then repeat with the dictionary in another domain and with `include_one_hop_neighbors` on and off.

### Tests and checks for User Story 3

- [x] T025 [P] [US3] Extend `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py`: one relation entry with `relationship_kind` `reference`, `label` the field name, the host as `source`, the dictionary as `target`, and the declared cardinals; the field row still carries `reference_qualname`; the payload validates against its schema; a reference to a dictionary in another domain is included with `include_one_hop_neighbors` and absent without it (FR-017, FR-021, FR-022; SC-005)
- [x] T026 [P] [US3] Extend `packages/aoa-demo/tests/test_demo_dictionary_graph.py`: the demo slice carries its reference relations with the field name as label and the dictionary as target (FR-013, FR-022; SC-002)
- [x] T027 [P] [US3] Extend `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts`: the SVG has one arrow per reference with the field label, the row still prints `→ Dict` once, the dictionary card has no code row and the code stays in the tooltip, a non-dictionary card is unchanged, and a legacy graph carrying the reference only as `reference_qualname` renders without a rebuild (FR-018, FR-019, FR-020; SC-005)

### Implementation for User Story 3

- [x] T028 [US3] Append the reference rows to `relation_sql` in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py`: `relationship_kind` `reference`, `label` the field name, `source_cardinality` `one`, `target_cardinality` `zero_many`, read from `entity_reference_edges` (FR-017, FR-018)
- [x] T029 [US3] Extend `neighbor_clause` in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py` to union `entity_reference_edges`, so a referenced dictionary from another domain joins the slice when neighbours are requested and stays out when they are not (FR-021)
- [x] T030 [US3] Adversarially drop the reference rows from `relation_sql`, confirm T025's reference tests and T026's slice test fail while the relation-edge tests in the same run pass, then restore (file: `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py`) (FR-027; SC-005)

**Checkpoint**: the payload and the SVG carry the reference once, the dictionary card is unchanged, and the cross-domain case behaves.

---

## Phase 5: User Story 4 — a refusal names the shape that is wrong (Priority: P3)

**Goal**: a union of two structural entities, a heterogeneous collection and a mapping each refuse with a message about that shape; none of them becomes accepted and every other refusal keeps its behaviour.

**Independent test**: declare each of the three shapes and read its message; then break the three messages back to the collection text and confirm the targeted test fails while a bare structural refusal still passes.

### Tests for User Story 4

- [x] T031 [P] [US4] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `A | B` for two structural entities is refused with a message naming both entities and asking for two fields, and it does not describe the union as a collection or offer `AssociationMany` (FR-023; SC-006)
- [x] T032 [P] [US4] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `tuple[A, B]` names the collection and both entities, and offers no single-target many-relation (FR-024; SC-006)
- [x] T033 [P] [US4] Add to `packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py`: `dict[str, A]` describes a mapping and offers no many-relation; the bare structural refusal, the homogeneous collection refusal and the dictionary collection refusal keep their current messages (FR-025, FR-026; SC-006)

### Implementation for User Story 4

- [x] T034 [US4] Add the shape classification and derive the three messages in `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`, keeping the owner and the field in every message and changing no accepted form (FR-023, FR-024, FR-025)
- [x] T035 [US4] Adversarially restore the collection message for the union, confirm T031 fails while T033's bare-structural control passes, then restore (file: `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py`) (FR-026, FR-027; SC-006, SC-007)

**Checkpoint**: the three shapes name themselves, and every other refusal is byte-identical to before.

---

## Phase 6: Polish & cross-cutting concerns

Exactly three tasks — the constitution's tail, in this order, and no other task absorbs them.

- [x] T036 Run `bash scripts/run_checks_with_log.sh` and take it to zero, including the client build, the Node checks, mypy, pylint, radon, vulture, packaging and every package's suite; confirm only the chunk-size advisory and the pending-deprecation warning remain, and record the tail (FR-029; SC-008)
- [ ] T037 Write the documentation in English — `docs/how-to/explicit-entity-fields.md` (the boundaries paragraph and the dictionary form table), `docs/reference/intents-and-invariants.md` (the dictionary graph row), `docs/tutorials/step-20-dictionaries.md` and the ERD case — with a case for every accepted form, every refusal and the three diagnostics, each case as a script under `examples/step_20_dictionaries/` and as a notebook, executed while written; no Russian draft (FR-030; SC-008)
- [ ] T038 Write the changelog article in `docs/CHANGELOG.md` for `aoa-action-machine` and `aoa-maxitor`: what a reader can now do — a dictionary reference is judged and drawn as a link, a collection of dictionary values is refused with the form that works, and a refusal names the shape that is wrong — in plain words, without a per-file account (FR-030; SC-008)

---

## Dependencies & execution order

### Story dependencies

- **US1 (phase 2)** has no dependency; it extends `entity_field_validator.py`.
- **US2 (phase 3)** depends on US1: the edge exists only for a form the rule accepts, and the not-a-graph-model refusal must exist before the edge can be emitted. It also touches `aoa-maxitor` in the same phase, because `DuckDBGraphResource` refuses an unknown edge type.
- **US3 (phase 4)** depends on US2: the payload reads the table US2 creates.
- **US4 (phase 5)** is independent of US1–US3 in behaviour, but it edits the same module as US1, so it follows the rule work to avoid a conflict.
- **Phase 6** follows every story, and T036 precedes T037, which precedes T038.

### Within a story

Tests first (T003–T008, T014–T017, T025–T027, T031–T033), then the implementation, then the adversarial reintroduction. A test that passes before its implementation is a test that proves nothing.

### Parallel opportunities

- T001 and T002 in Setup.
- Every test task marked `[P]`: T003–T008 (one module, one case each), T014–T017 (one module, four cases), T025–T027 (one Python payload test, one demo test, one TypeScript check — different files), T031–T033.
- T018's edge module and T020's schema entry are different files and can be written together, but T019 depends on T018.
- T022 is the only `aoa-maxitor` task in phase 3; it can be written beside T018–T021 but must ship in the same commit.

### Parallel example — Phase 4 tests

```text
Task: T025 — payload gains a reference relation; the row keeps reference_qualname; cross-domain on and off
Task: T026 — the demo slice carries the reference with the field name as label
Task: T027 — the SVG has the arrow and the label; the dictionary card is unchanged; a legacy graph renders
```

## Implementation strategy

### MVP first

US1 alone (phase 2) is the MVP: the rule judges a dictionary field, the two accepted forms work, and the six refusals replace the silent acceptance. Validate it with `quickstart.md` proofs 1–6, then commit on instruction.

### Incremental delivery

Add one phase at a time, each a commit on instruction, each leaving the tree green:
US2 → US3 → US4. US2 is the widest because it crosses into `aoa-maxitor`; US4 is the smallest
and can be taken last without blocking anything.

### What is deliberately not a task

- A many-reference form for a collection of dictionary values — the spec refuses it here and leaves the shape to a later issue.
- A wrapper type around the bare dictionary reference — spec D-1 keeps the bare type.
- A storage migration or a graph rebuild — the code column and the graph document are untouched.
- A second description or requiredness rule for dictionary references — FR-032 refuses one.
- A Russian draft of any page — the spec's Out of scope says so; the task list's own `tasks.ru_draft.md` is the one exception, as for #244 and #249.
- Acting on the two accepted remarks of the check run.
- A commit, a push, a pull request or a merge: phase boundaries are commit boundaries only on the maintainer's instruction.

## Format validation

Every task above carries a checkbox, an ID, an optional `[P]`, a story label inside a story phase, and at least one concrete file path; the three tail tasks carry no story label, and none of them was absorbed by an earlier phase.
