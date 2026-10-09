# Tasks: Entity specialization — one field, N extension tables, chosen by a classifier

**Input**: Design documents from `specs/002-entity-specialization/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. The specification's acceptance criteria are stated as break-and-restore checks (SC-002), so every rule task is followed by the test that proves it fires and that restoring the declaration passes.

**Organization**: tasks are grouped by user story so each story is independently implementable and testable. Tasks are numbered in the order they will actually be executed. Phase 2 is the declaration vocabulary; the wrapper value type of the first draft is gone, because the field holds a container that carries the identifier, the variant and the row (see [research.md](./research.md), the superseding decision).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (US1…US4)
- Every task names the exact file it touches

## Path Conventions

Repository root is the working directory. Engine paths are `packages/aoa-action-machine/…`, consumer paths are `packages/aoa-maxitor/…`.

---

## Phase 1: Setup

**Purpose**: the shared model every later phase runs against — a head with a classifier field and its extensions.

- [x] T001 Add the worked model to the relations example so every later phase has something to run against: a head with a classifier field and five extension entities with their own fields, in `examples/step_21_relations/02_specialization.py` (script) and `examples/step_21_relations/02_specialization.ipynb` (same case, cell by cell)
---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the declaration vocabulary — the two containers, the marker that names what selects, and the two errors. Every user story depends on it.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [x] T002 Create `packages/aoa-action-machine/src/aoa/action_machine/domain/specialization_containers.py` holding `Specialization[T]` and `Generalization[T]` — frozen pydantic models, `Generic` in the house style (`class Specialization[T](BaseModel)`), each with `id`, an optional `entity` excluded from `repr` (a head and its extension reference each other, and printing one would print the other forever), and `variant` on the head side — plus the `Classifier` marker: frozen, `__slots__`, `__eq__` / `__hash__` / `__repr__`, constructing as `Classifier("media", "first", "repress")` — the choosing field first, then the codes in declaration order — refusing a wrong or empty argument (`TypeError` / `ValueError`), with an `AI-CORE` block on all three. **In the same task**, make `Inverse.target_entity` optional (`None` by default) so the head-side form `Inverse(field_name="event")` stops raising `TypeError`, and refuse an `Inverse` that names neither a target nor a field. Export all three from `domain/__init__.py`. The earlier `By` and `Generalization(...)` marker classes are removed: the containers carry the alternatives and the code
- [x] T003 [P] Add `SpecializationDeclarationError` (build-time declaration violations, per [research.md](./research.md) D5) and `UndeclaredSpecializationVariantError` (a code arriving from data that no alternative declares, FR-027) to `packages/aoa-action-machine/src/aoa/action_machine/domain/exceptions.py`, with the module's exception-map docstring updated and both names re-exported from `packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py`
---

## Phase 3: User Story 1 — one head field that points at one of N extension tables (Priority: P1) 🎯 MVP

**Goal**: a head parameterises a container with the union of N extensions and names the codes beside it; the build succeeds; the graph carries the alternatives and the code-to-class mapping; the field holds a link that keeps its identifier and variant even when the row is not loaded.

**Independent Test**: declare one head with three extensions, build, and read the axis back — three classes, three codes, one classifier (quickstart Scenario 1).

- [x] T004 [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py` with the `EntitySpecializationIntentResolver` row and its parser, per [data-model.md](./data-model.md) §2. Recognise a field whose **type is a subscripted `Specialization`** — the container alone is the discriminator, because the `Classifier` marker also sits on every extension's reverse field and a marker never says which side a field is on. A container without a `Classifier` is a declaration error, not a skip. Read the alternatives from the container's type argument in declaration order: `annotation.__pydantic_generic_metadata__["args"][0]`, because pydantic materialises a real class and `get_args` on that class returns nothing. Read the markers from **`FieldInfo.metadata`** — `classifier_field` from `Classifier.field`, the declared `codes` from `Classifier.code_values`, `inverse_field` from `Inverse(field_name=…)`, plus `deprecated` and `omit_graph_edge` — and not from `get_type_hints(..., include_extras=True)`, which raises on a model whose forward references do not resolve while `model_fields` stays readable (measured; [research.md](./research.md) D1). Read each alternative's own code from its reverse field, which carries a single-member `Classifier`, and expose the derived `code_to_target` mapping. Provide `gather_entity_specialization_intent_resolvers(host_cls)`
- [ ] T005 [US1] Expose the parser through the entity intent facade: add `resolve_entity_specializations` to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_intent_resolver.py` and the re-export to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/__init__.py`
- [ ] T006 [P] [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_specialization_field_graph_node.py` for the vertex `entity_specialization_field` per [contracts/graph-payload.md](./contracts/graph-payload.md): `label` = the head's field name, `properties` = `description`, `classifier_field`, `alternatives` (the `"<code> -> <qualname>"` list in declaration order), `optional` = `True`
- [ ] T007 [P] [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_specialization_graph_edge.py` for the edge `entity_specialization` (head → each alternative): one edge per union member, `relationship = "Association"` (via `AssociationGraphEdge`, so the edge stays in the full-graph payload), `is_dag = False`, `target_node_id` = the alternative's qualname, and the full property set of [contracts/graph-payload.md](./contracts/graph-payload.md) including `classifier_field`, `classifier_value` and the repeated `alternatives` list
- [ ] T008 [US1] Wire both into `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py`: add the `specializations` edge list and an `EntitySpecializationFieldGraphNode` companion per axis, and return them from `get_all_edges` and `get_companion_nodes`
- [ ] T009 [US1] Stop the scalar-field path from swallowing the new field. **Depends on T004**: a specialization field's type is a container, not a union, so the old question ("is this a relation container?") answers no and the field would be taken for a column. Make the graph's scalar-field path recognise a field carrying a `Classifier` marker, and exclude such field names from the `entity_field` scalar edges in `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py` the way relation names are excluded today (line 64). Both halves are needed: without the first the exclusion holds only by accident and breaks the moment the resolver changes; without the second the ERD shows a column carrying a container class as its type
- [ ] T010 [P] Write the container and marker tests in `packages/aoa-action-machine/tests/action_machine/domain/test_specialization_containers.py`: a subscripted container is a real class; a narrower subscription refuses another alternative and a class outside the union; `entity` may be `None` and the link still carries `id` and `variant` for the head side; `repr` of a mutually referencing pair terminates; both containers are frozen; and `Classifier` refuses a non-string or empty field name and code, exposes `by` and `variants` in order, and compares and hashes by them
- [ ] T011 [P] [US1] Write the mechanism test in `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_specialization_resolver.py`: a head with three alternatives parses to three classes, three codes and one classifier field, in declaration order; the derived mapping pairs a class with its own declared code; **the two-sided comparison holds** — every class in the union declares exactly one code, every declared code belongs to a class, the sets are equal and the sizes agree — and reports what is missing when a class declares no code, when one declares two, when a code is repeated, and when a class outside the union is named; a field with no `Classifier` is not a specialization field; `NoGraphEdge()` is honoured
- [ ] T012 [P] [US1] Write the graph test in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_graph.py`: building a machine with one head and three extensions succeeds; the head node carries three `entity_specialization` edges and one `entity_specialization_field` vertex; no `entity_field` scalar edge exists for the specialization field; the payload passes the interchange JSON schema; and the runtime facts the design rests on — a container carrying a member's row is accepted and reads back with its `id` and `variant`, a link with no row loaded still reads its identifier and variant, and a row whose class the union does not list is refused; plus FR-025/SC-005: a model declaring **no** specialization produces the same graph as before the change, compared structurally (vertex by vertex, edge by edge with properties, so list order alone does not fail it), and a payload of that model still validates against `GRAPH_JSON_SCHEMA` (model the fixture on `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_generalization.py`)
- [ ] T013 [US1] Run the MVP checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/ -v -k specialization`, then run the worked example from T001 against the parser, fix whatever it reveals, and record the output it actually prints in the example's docstring
**Checkpoint**: US1 is a usable increment on its own — the model builds, the field holds a link, and the graph carries the alternatives and the mapping. Nothing is validated yet, and the ERD does not show it.

---

## Phase 4: User Story 2 — a broken declaration fails at build, naming the place (Priority: P2)

**Goal**: every build rule of [data-model.md](./data-model.md) §2 runs in one global pass, and every violation is a named `SpecializationDeclarationError` instead of a silently lost or redirected relation.

**Independent Test**: for each rule, break exactly that declaration, build, confirm the named error and no other; restore and confirm the build passes (quickstart Scenario 2, SC-002).

- [ ] T014 [US2] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py` implementing the build rules of [data-model.md](./data-model.md) §2 as one pass over the entity nodes, raising `SpecializationDeclarationError` naming the class, the field and the rule. **The two-sided code check is the centre of it** (FR-014): for each axis compare the codes the head names against the codes the classes declare, in both directions, with equal sizes — every class declares exactly one, every code belongs to a class, a repeated code fails. The other global rules — mutuality in both directions, closure, one head per class, one field per classifier — need the whole set; the axis rules — a type argument that is not a declared entity, an alternative subclassing another or the head, `Classifier(field=…)` naming a relation / a class constant / a property / a missing field / the field itself, a code the classifier's type cannot hold — are decided per axis. Type compatibility follows [research.md](./research.md) D6: `str` accepts any non-empty string, a `Literal` its members, an `Enum` subclass its member values, anything else is refused
- [ ] T015 [US2] Call the pass from `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py` inside `build()`, after `_single_pass_validate_and_wire` and before `_validate_dag_acyclicity` (lines 143–146), skipping it entirely when no entity declares a specialization so an unchanged model takes no new path
- [ ] T016 [P] [US2] Write the axis-rule tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py`: a union member that is not a declared entity; a code the classifier's type cannot hold; an alternative subclassing another or the head; a missing `Classifier`; `Classifier(field=…)` naming a relation / a `ClassVar` / a property / a missing field / the field itself; `NoInverse()` on either side; a partner field targeting an ancestor; and a head whose field is not parameterised by the container at all
- [ ] T017 [P] [US2] Write the global-rule tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_global.py`: a union member with no `Generalization` marker; a member whose marker names another head or another field; mutuality's second direction — a class pointing at the axis whose class the union does not list; closure — a member whose partner field belongs to another axis; a class named by two heads; two axes of one head naming different class sets; a partner field for an axis the head never declares; and a head→extension cycle
- [ ] T018 [US2] Write the break-and-restore sweep in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_sweep.py`: **one case per build rule**, taken from the rule table of [data-model.md](./data-model.md) §2 rather than from the other two test files, each asserting that the build fails with the named error **and** that restoring the single broken declaration passes with no other change (SC-002); assert the error names the class, the field and the rule
- [ ] T019 [US2] Run the checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/ -v -k specialization` and confirm each rule fires alone — a model breaking two rules at once must report one of them rather than an unrelated failure
**Checkpoint**: US2 is independently valuable — a developer gets a build error instead of a wrong diagram or a missing edge, even before the ERD work.

---

## Phase 5: User Story 3 — the ERD and the graph show the variants (Priority: P3)

**Goal**: one field row naming all alternatives and the classifier, N generalization relations with the right notation, and a store that accepts both new types.

**Independent Test**: build a system with a head and three extensions, read the ERD payload and the store, and compare the row, the relations and the edges with the declared model (quickstart Scenario 3, SC-006).

- [ ] T020 [US3] Extend `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`: add the `$defs` entries for `entity_specialization_field` (vertex), `entity_specialization` (link) and the generalization branch with properties (`relationship` const `Generalization`, the four property keys), add both branches to `link.oneOf` and the vertex to the vertex `oneOf` — the existing `parent_*` entries allow `maxProperties: 0`, so the generalization branch cannot be reused as-is
- [ ] T021 [P] [US3] Emit the extension→head edge: a `parent_entity` generalization edge carrying `field_name`, `inverse_field`, `classifier_value` and `head_entity_id`, built where the extension's `Generalization` marker is read, so every declared alternative produces exactly one, and `relationship = "Generalization"` keeps them out of the full-graph payload by the existing predicate ([research.md](./research.md) D4)
- [ ] T022 [P] [US3] Write the schema test in `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_specialization.py`: a payload with the new vertex and both new edges validates against `GRAPH_JSON_SCHEMA`, and a payload missing a required property is rejected — the schema is `additionalProperties: false` and enforced, so this test is what keeps it honest
- [ ] T023 [US3] Register both new types in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` at all five sites per type ([research.md](./research.md) D8): `CREATE TABLE` for `entity_specialization_field` and `entity_specialization_edges`, the `_EDGE_TABLE_NAMES` tuple, the `nodes` and `edges` union-view branches, the fill function plus its dispatch line for both, and `known_nodes` / `known_edges` in `_assert_no_unknown_graph_types`
- [ ] T024 [P] [US3] Add the new vertex type to both registries in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_node_types_action.py`: `_DUCK_SLUG_TO_INTERCHANGE` and `NODE_TYPE_FILL_COLORS`
- [ ] T025 [US3] Extend the ERD payload in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py` per [contracts/graph-payload.md](./contracts/graph-payload.md): one field row per axis (`name` = `<field> | <code>… (by <classifier>)`, `type` = the alternatives' labels joined by `" | "`, `foreign_key = true`, `field_id` = the vertex id) instead of N `FK -> ` rows, one relation entry per alternative labelled with its code, and the new edge table in the `neighbor_clause` so `include_neighbors=True` still reaches the extensions
- [ ] T026 [US3] Widen the field-row and relation contracts in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py`: the field-row object is `additionalProperties: false` and validated at runtime, so the keys the new row needs must be declared before the row can travel
- [ ] T027 [US3] Emit the notation in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`: for a generalization relation line use `arrowhead=empty style=solid penwidth=1` (the attributes the use-case builder already uses), keep `arrowhead=vee` for the association-style `entity_specialization` edges so the ERD gains a notation vocabulary rather than losing one, and carry the kind on `ErdRelation`
- [ ] T028 [P] [US3] Write the store and ERD tests in `packages/aoa-maxitor/tests/test_entity_specialization_erd.py`, modelled on `test_duckdb_depends_edges_mode.py` and `test_list_entities_duckdb_sql.py`: both new tables hold their rows and the payload JSON round-trips through the `edges` view; `ListEntitiesAction._slice_payload` returns exactly one field row for the head's field with all five codes and the classifier, and exactly five relation entries; a scalar field on the same entity is still exactly one `entity_field` row
- [ ] T029 [US3] Write the registration guard test in `packages/aoa-maxitor/tests/test_duckdb_specialization_type_registration.py`, modelled on `test_duckdb_access_decide_type.py`: an unregistered node or edge type raises `KeyError`, so dropping either registration without dropping the emitter fails loudly
- [ ] T030 [US3] Prove the full-graph exclusion is intended, in `packages/aoa-maxitor/tests/test_duckdb_parent_generalization_edges.py`: with the new edges loaded, the full-graph payload contains the `entity_specialization` edges and **none** of the `parent_entity` ones, so the exclusion is asserted rather than inherited by accident
- [ ] T031 [US3] Run the checkpoint: `uv run --extra dev pytest packages/aoa-maxitor/tests/ -v -k specialization`, then build the client (`cd packages/aoa-maxitor/client && npm ci && npm run build`) and record the generated DOT and the rendered diagram in the example from T001
**Checkpoint**: the diagram says what the model says. US3 does not depend on US2 — it can be built and demonstrated while the rule sweep is still incomplete.

---

## Phase 6: User Story 4 — a code that no extension declares (Priority: P4)

**Goal**: the declared mapping is available to the code that reads a row, so that a code nobody declared fails loudly instead of reading as "no continuation".

**Independent Test**: ask the axis for the class a declared code denotes and get it; ask for a code nobody declared and get a named failure (quickstart Scenario 4, SC-008).

- [ ] T032 [US4] Add code resolution to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py`: given an axis and a code, return the extension class the mapping declares for it, or raise `UndeclaredSpecializationVariantError` naming the code and the field (FR-027). This is what a resource calls after reading a row, so that the "which table does this row continue in" decision is written once in the framework and invoked explicitly by the developer — no resolution happens behind the developer's back, and nothing is inferred from a class name
- [ ] T033 [US4] Cover the resolution in `packages/aoa-action-machine/tests/action_machine/runtime/test_specialization_resolution.py`: a declared code resolves to its own class for every member of an axis; an undeclared code fails naming the value and the field; a code from another axis does not resolve; and the mapping is the one each extension declares, so removing a `Generalization` marker from one extension removes exactly that code
- [ ] T034 [US4] Cover the assignment contract in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_assignment.py` on a real headline model: the object built for a resolved code goes into the field and reads back as the same object; an object of a class the union does not list is refused with `ValidationError`; a bare identifier is refused too, because pydantic tries to build one of the alternatives; and a field left empty reads as nothing rather than as a substituted type (FR-026, FR-028, FR-029)
- [ ] T035 [P] [US4] Pin the introspection and process-mining boundary in `packages/aoa-ocel/tests/test_ocel_specialization_boundary.py`, and make it discriminate: the extension object carried in the field is **not** reported as a foreign key by `BaseEntity.get_foreign_keys()` (the field holds an entity, not a relation container), while `_materialize_frame` on a frame whose root carries it returns exactly one object. Assert both halves — with only the second, the test passes whether or not anything reports it, which pins nothing
- [ ] T036 [US4] Run the checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/ packages/aoa-ocel/tests/ -v -k specialization`
**Checkpoint**: all four stories are in. The failure modes the feature exists to remove are gone: no silent wrong table, no silent missing edge, no silently substituted type.

---

## Phase 7: The closing three steps (constitution, Principle VI)

**Purpose**: the constitution reserves **exactly these three tasks, in this order**, and no other task may absorb them.

- [ ] T037 [US1] [US2] [US3] [US4] Run the repository check to zero: `bash scripts/run_checks_with_log.sh` from the repository root; fix every remark it reports — none triaged away, none accepted as known, none left for later; review whatever `ruff check --fix` changed, because the run edits the code; the only two remarks that stay are the Vite chunk-size advisory and LangGraph's pending-deprecation warning
- [ ] T038 [US1] [US2] [US3] [US4] Write the documentation, after the code is settled: `docs/tutorials/step-21-relations.md` gains the specialization case with examples that actually ran (declaring the head and the extensions, the multi-axis shape, the runtime value, and the failure cases kept apart from the working ones); `docs/tutorials/step-26-maxitor.md` gains the ERD and full-graph view of the same model with the generated DOT and the rendered picture from T031; `docs/reference/intents-and-invariants.md` gains the rules under **Entity relations**, naming them for what they are — the first relation checks implemented in code, since the ownership matrix and the mandatory inverse documented there are still not enforced; `docs/reference/glossary.md` gains the terms; and `examples/step_21_relations/02_specialization.py` plus its notebook are the runnable form of every case, executed while they are written
- [ ] T039 [US1] [US2] [US3] [US4] Write the changelog last, as one article: `docs/CHANGELOG.md` gets a single readable piece about what this work created — a head row that continues in one of several tables, chosen by a value the model declares, what the diagram now shows, and what a developer has to know to use it — in plain words, without technical detail, without a per-file account and without a list of commits

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** → the shared model; T012, T013 and T031 read it, so it is cheapest to write once, early
- **Phase 2 (Foundational)** → blocks every story; T002 is the containers, the marker and the second form of `Inverse`, and T003 the two errors
- **US1 (Phase 3)** → needs Phase 2 only; it is the MVP
- **US2 (Phase 4)** → needs US1's parser (T004); its rules are about declarations the parser produces
- **US3 (Phase 5)** → needs US1's graph node and edge (T006, T007); **does not need US2** and can run in parallel with it
- **US4 (Phase 6)** → needs US1's parsed axis (T004); does not need US2 or US3
- **Phase 7** → needs every story; T039 is last of all

### Within a story

- Implementation before its tests: T004→T011/T012, T014→T016/T017/T018, T023→T028/T029/T030, T032→T033
- T009 needs T004's parser: a specialization field's type is a container, so the old "is this a relation container?" question answers no and the field would be taken for a column — the exclusion depends on the field being recognised first
- T010, the container and marker tests, may run anywhere after T002. It sits after the parser because the parser is what makes the capability usable, and the containers were exercised by hand while T002 was written
- The break-and-restore sweep (T018) depends on the whole validator (T014) and the coordinator hook (T015)
- T023 depends on nothing in the engine at runtime, only on the payload shape, so it can start as soon as the contracts are read
- T031 records the generated DOT and the rendered diagram, so it runs after the client change (T027)

### Parallel opportunities

`[P]` marks tasks that touch different files and depend on nothing incomplete:

- **T003, T010** — the two errors and the container tests, either side of the parser
- **T006, T007** — the field vertex and the specialization edge
- **T011, T012** — the parser test and the graph test
- **T016, T017** — the axis-rule and global-rule test files
- **T021, T022** — the generalization edge and the schema test
- **T024, T028** — the node-type registries and the store tests (T027 shares `list_node_types_action.py` with T024, so it is not parallel with it)
- **T035** — the process-mining boundary test, while the engine side of US4 is finished

## Parallel Example: User Story 3

```bash
# independent files, one pass:
Task: "Extend graph_json_schema.py with the three $defs and two link.oneOf branches"
Task: "Emit the parent_entity generalization edge from the extension side"
Task: "Write the schema test in tests/action_machine/graph/test_graph_json_schema_specialization.py"

# and after T023 lands:
Task: "Register the new vertex type in list_node_types_action.py"
Task: "Write the store and ERD tests in packages/aoa-maxitor/tests/test_entity_specialization_erd.py"
Task: "Emit notation in client/src/lib/buildDotSource.ts"
```

---

## Implementation Strategy

### MVP first

1. Phase 1 (T001) and Phase 2 (T002–T003)
2. Phase 3 (T004–T013)
3. **Stop and validate**: the model builds, the field holds a link, the graph carries the alternatives and the code-to-class mapping
4. That is a usable increment: a developer can declare the relation and read it back

### Then, in any order

- Phase 4 (US2) — the rule sweep, which is what makes the declaration safe to write
- Phase 5 (US3) — the ERD and the store, which is what makes it reviewable by people who do not read the code
- Phase 6 (US4) — the runtime, which is what makes a data mistake visible

Each of the three is independently testable and independently demonstrable; US3 does not wait for US2.

### Then the closing three

- T037 the check run to zero → T038 the documentation → T039 the changelog. In that order, and nothing else absorbs them.

---

## Notes

- One phase is one commit; nothing is committed without an explicit instruction in the current turn (constitution, Principle I)
- English everywhere it is read as code or history (Principle II); module headers (III); AI-CORE blocks on the new public classes (IV); one-line docstrings (V)
- Verification is adversarial: break the code the way the new test must catch, confirm that test fails and no other does, restore
- The two store registrations are the highest-risk tasks: a missed site does not degrade the diagram, it aborts the whole load
