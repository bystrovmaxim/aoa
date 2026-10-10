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
- [x] T005 [US1] Expose the parser through the entity intent facade: add `resolve_entity_specializations` to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_intent_resolver.py` and the re-export to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/__init__.py`
- [x] T006 [P] [US1] Decide, and record, that the field keeps **one** row in the diagram: the head's field keeps the `EntityField` row every other field has, and that row is the single entry the diagram shows. A separate vertex was written first and then dropped for two reasons: it would duplicate data the edges already carry (the alternatives, their codes, the classifier), and its natural key — `<head qualname>:<field name>` — is exactly the column row's id, so it could not have coexisted with it. Measured: the two nodes carry the same id and different `node_type`. The column's `field_type` is what the diagram shows, and the ERD work formats it
- [x] T007 [P] [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_specialization_graph_edge.py` for the edge `entity_specialization` (head → each alternative): one edge per union member, `relationship = "Association"` (via `AssociationGraphEdge`, so the edge stays in the full-graph payload), `is_dag = False`, `target_node_id` = the alternative's qualname, and the full property set of [contracts/graph-payload.md](./contracts/graph-payload.md) including `classifier_field`, `classifier_value` and the repeated `alternatives` list
- [x] T008 [US1] Leave the scalar-field path alone, and record why. The field **stays a column** — its `entity_field` row belongs in the diagram exactly like every other field, and a head whose continuation lives elsewhere must show the field it continues through. No exclusion is added: the field is not a relation container, so it never entered the ownership relation set, and nothing about it is emitted twice. Verified on a built graph: the head carries three `entity_specialization` edges **and** the `entity_field` edge for the same field, and every edge target resolves to a node
- [x] T009 [US1] Wire the edges into `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py`: a `specializations` list beside `relations`, built from `EntitySpecializationGraphEdge.get_entity_specialization_edges`, and returned from `get_all_edges` together with the domain, relations, lifecycles and field edges
- [x] T010 [P] Write the container and marker tests in `packages/aoa-action-machine/tests/action_machine/domain/test_specialization_containers.py`: a subscripted container is a real class; a narrower subscription refuses another alternative and a class outside the union; `entity` may be `None` and the link still carries `id` and `variant` for the head side; `repr` of a mutually referencing pair terminates; both containers are frozen; and `Classifier` refuses a non-string or empty field name and code, exposes `by` and `variants` in order, and compares and hashes by them
- [x] T011 [P] [US1] Write the mechanism test in `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_specialization_resolver.py`: a head with three alternatives parses to three classes, three codes and one classifier field, in declaration order; the derived mapping pairs a class with its own declared code; **the two-sided comparison holds** — every class in the union declares exactly one code, every declared code belongs to a class, the sets are equal and the sizes agree — and reports what is missing when a class declares no code, when one declares two, when a code is repeated, and when a class outside the union is named; a field with no `Classifier` is not a specialization field; `NoGraphEdge()` is honoured
- [x] T012 [P] [US1] Write the graph test in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_graph.py`: building a machine with one head and three extensions succeeds; the head node carries three `entity_specialization` edges and keeps the field as a column; the field's own `entity_field` row is still emitted, exactly once; the payload passes the interchange JSON schema; and the runtime facts the design rests on — a container carrying a member's row is accepted and reads back with its `id` and `variant`, a link with no row loaded still reads its identifier and variant, and a row whose class the union does not list is refused; plus FR-025/SC-005: a model declaring **no** specialization produces the same graph as before the change, compared structurally (vertex by vertex, edge by edge with properties, so list order alone does not fail it), and a payload of that model still validates against `GRAPH_JSON_SCHEMA` (model the fixture on `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_generalization.py`)
- [x] T013 [US1] Run the MVP checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/ -v -k specialization`, then run the worked example from T001 against the parser, fix whatever it reveals, and record the output it actually prints in the example's docstring
**Checkpoint taken**: 48 tests named `specialization`, the whole action-machine suite green at 2418, `ruff`, `mypy` and `pylint` clean, and the worked example runs end to end — it now reads its axis through the framework's own resolver rather than a hand-read annotation, prints what the parser found, and prints the graph it produces: three `entity_specialization` edges and the `pressing` column. The example's docstring carries that output verbatim, checked against a fresh run.

**Checkpoint**: US1 is a usable increment on its own — the model builds, the field holds a link, and the graph carries the alternatives and the mapping. Nothing is validated yet, and the ERD does not show it.

---

## Phase 4: User Story 2 — a broken declaration fails at build, naming the place (Priority: P2)

**Goal**: every build rule of [data-model.md](./data-model.md) §2 runs in one global pass, and every violation is a named `SpecializationDeclarationError` instead of a silently lost or redirected relation.

**Independent Test**: for each rule, break exactly that declaration, build, confirm the named error and no other; restore and confirm the build passes (quickstart Scenario 2, SC-002).

- [x] T014 [US2] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py` implementing the build rules of [data-model.md](./data-model.md) §2 as one pass over the entity nodes, raising `SpecializationDeclarationError` naming the class, the field and the rule. **The two-sided code check is the centre of it** (FR-014): for each axis compare the codes the head names against the codes the classes declare, in both directions, with equal sizes — every class declares exactly one, every code belongs to a class, a repeated code fails. The other global rules — mutuality in both directions, closure, one head per class, one field per classifier — need the whole set; the axis rules — a type argument that is not a declared entity, an alternative subclassing another or the head, `Classifier(field=…)` naming a relation / a class constant / a property / a missing field / the field itself, a code the classifier's type cannot hold — are decided per axis. Type compatibility follows [research.md](./research.md) D6: `str` accepts any non-empty string, a `Literal` its members, an `Enum` subclass its member values, anything else is refused
- [x] T015 [US2] Call the pass from `packages/aoa-action-machine/src/aoa/action_machine/graph/core/node_graph_coordinator.py` inside `build()`, after `_single_pass_validate_and_wire` and before `_validate_dag_acyclicity` (lines 143–146), skipping it entirely when no entity declares a specialization so an unchanged model takes no new path
- [x] T016 [P] [US2] Write the axis-rule tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py`: a union member that is not a declared entity; a code the classifier's type cannot hold; an alternative subclassing another or the head; a missing `Classifier`; `Classifier(field=…)` naming a relation / a `ClassVar` / a property / a missing field / the field itself; `NoInverse()` on either side; a partner field targeting an ancestor; and a head whose field is not parameterised by the container at all
- [x] T017 [P] [US2] Write the global-rule tests in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_global.py`: a union member with no `Generalization` marker; a member whose marker names another head or another field; mutuality's second direction — a class pointing at the axis whose class the union does not list; closure — a member whose partner field belongs to another axis; a class named by two heads; two axes of one head naming different class sets; a partner field for an axis the head never declares; and a head→extension cycle
- [x] T018 [US2] Write the break-and-restore sweep in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_sweep.py`: **one case per build rule**, taken from the rule table of [data-model.md](./data-model.md) §2 rather than from the other two test files, each asserting that the build fails with the named error **and** that restoring the single broken declaration passes with no other change (SC-002); assert the error names the class, the field and the rule
- [x] T019 [US2] Run the checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/ -v -k specialization` and confirm each rule fires alone — a model breaking two rules at once must report one of them rather than an unrelated failure
**Checkpoint taken**: 51 tests named `specialization` in the graph tree, the whole action-machine suite green at 2455, `ruff` and `mypy` clean, and the worked example still builds with three edges and its column. The precedence requirement is now pinned by three tests rather than assumed: a model with two faults reports the more fundamental one, a code that cannot be stored is refused on its own account before any question of matching is asked, and five runs of the same model produce one identical report. One expectation was wrong when written — the numeric-classifier case — and the run corrected it rather than the code.

**Checkpoint**: US2 is independently valuable — a developer gets a build error instead of a wrong diagram or a missing edge, even before the ERD work.

---

## Phase 5: User Story 3 — the ERD and the graph show the variants (Priority: P3)

**Goal**: one field row naming the axis, the alternatives grouped in a container the reader can see, N generalization relations with the right notation, and a store that accepts the new edge type.

**Independent Test**: build a system with a head and three extensions, read the ERD payload and the store, and compare the row, the relations and the edges with the declared model (quickstart Scenario 3, SC-006).

- [x] T020 [US3] Extend `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py`: add the `$defs` entry for `entity_specialization` (link) and the generalization branch with properties (`relationship` const `Generalization`, the four property keys), add both branches to `link.oneOf` — the existing `parent_*` entries allow `maxProperties: 0`, so the generalization branch cannot be reused as-is
- [x] T021 [P] [US3] Emit the extension→head edge: a `parent_entity` generalization edge carrying `field_name`, `inverse_field`, `classifier_value` and `head_entity_id`, built where the extension's `Generalization` marker is read, so every declared alternative produces exactly one, and `relationship = "Generalization"` keeps them out of the full-graph payload by the existing predicate ([research.md](./research.md) D4)
- [x] T022 [P] [US3] Write the schema test in `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_specialization.py`: a payload with the new vertex and both new edges validates against `GRAPH_JSON_SCHEMA`, and a payload missing a required property is rejected — the schema is `additionalProperties: false` and enforced, so this test is what keeps it honest
- [x] T023 [US3] Register the new edge kind in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` at every site a type must be known ([research.md](./research.md) D8): `CREATE TABLE`, the table-name tuple, the `edges` union-view branch, the fill function plus its dispatch line, and `known_edges`. **One type, not two** — a specialization adds no vertex, so nothing new goes into `known_nodes` or the `nodes` view. A missed site does not degrade a diagram: `_assert_no_unknown_graph_types` raises and the whole load dies, which is why T029 guards it
- [x] T024 [P] [US3] **Nothing to register here, and that is the finding.** The task was written to add a new **vertex** kind to these registries, from the design in which the axis had a vertex of its own; the vertex was dropped (T006) and the field stayed a column, so no new node kind exists to declare. Checked all three places rather than assuming: `_DUCK_SLUG_TO_INTERCHANGE` and `NODE_TYPE_FILL_COLORS` in `list_node_types_action.py`, and `graph_node_disk_icons.ts` in the client — every one of them is keyed by **node** type (`Entity`, `EntityField`, `Lifecycle`, …), and the edges reach the picture as labels rather than as registered kinds. A registry entry with no node behind it would be a row the store can never produce
- [x] T025 [US3] Extend the ERD payload in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py` per [contracts/graph-payload.md](./contracts/graph-payload.md): one field row per axis (`name` = `<field> (by <classifier>)`, `type` = `Class (code)` per alternative joined with `" | "`, with the `Entity` suffix dropped for display — the contract says why each half is there), **one relation line per axis into the axis container** rather than one per alternative (FR-029), and a **group** per axis carrying its `group_id`, its `label` and its `members` — the container the client draws around the alternatives (FR-026). A group is emitted only for an axis with more than one alternative: one alternative is a plain relation, and a box around one table would claim a choice that does not exist (FR-028). **The group is ERD-only (FR-030)**: no other drawing gains it, and none needs a flag to switch it off — the full-graph, use-case and lifecycle payloads have no notion of one
- [x] T026 [US3] Widen the field-row, relation and group contracts in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py`: the field-row object is `additionalProperties: false` and validated at runtime, so the keys the new row needs must be declared before the row can carry them, and the **group** object needs its own declaration with `additionalProperties: false` for the same reason
- [x] T027 [US3] Emit the container and the notation in `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`: draw every group as a Graphviz `subgraph cluster_<id>` with its label on the boundary, declaring its member tables **inside the subgraph and nowhere else** — Graphviz gives a node to the first subgraph that declares it, so a member declared twice would silently fall out of the container. Use `arrowhead=vee` for the axis line (head to container) and `arrowhead=empty style=solid penwidth=1` for the generalization line (extension to head), both taken from `buildDomainUseCaseDotSource.ts` rather than invented. A table outside any axis keeps the plain line it has today
- [x] T028 [P] [US3] Write the store and ERD tests in `packages/aoa-maxitor/tests/test_entity_specialization_erd.py`, modelled on `test_duckdb_depends_edges_mode.py` and `test_list_entities_duckdb_sql.py`: both new tables hold their rows and the payload JSON round-trips through the `edges` view; `ListEntitiesAction._slice_payload` returns exactly one field row for the head's field with all five codes and the classifier, and exactly five relation entries; a scalar field on the same entity is still exactly one `entity_field` row
- [x] T029 [US3] Write the registration guard test in `packages/aoa-maxitor/tests/test_duckdb_specialization_type_registration.py`, modelled on `test_duckdb_access_decide_type.py`: an unregistered node or edge type raises `KeyError`, so dropping either registration without dropping the emitter fails loudly
- [x] T030 [US3] Prove the full-graph exclusion is intended, in `packages/aoa-maxitor/tests/test_duckdb_parent_generalization_edges.py`: with the new edges loaded, the full-graph payload contains the `entity_specialization` edges and **none** of the `parent_entity` ones, so the exclusion is asserted rather than inherited by accident
- [x] T031 [US3] Run the checkpoint: `uv run --extra dev pytest packages/aoa-maxitor/tests/ -v -k specialization`, then build the client (`cd packages/aoa-maxitor/client && npm ci && npm run build`) and record the generated DOT and the rendered diagram in the example from T001. **The recorded rendering must show the container**, and the recorded DOT must show the member tables declared inside the `subgraph cluster_` and not outside it — the container is the part of this phase no test can check, since the client has no test runner, so the picture is the evidence

---

## Phase 6: User Story 4 — a code that no extension declares (Priority: P4)

**Goal**: the declared mapping is available to the code that reads a row, so that a code nobody declared fails loudly instead of reading as "no continuation".

**Independent Test**: ask the axis for the class a declared code denotes and get it; ask for a code nobody declared and get a named failure (quickstart Scenario 4, SC-008).

- [ ] T032 [US4] Add code resolution to `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py`: given an axis and a code, return the extension class the mapping declares for it, or raise `UndeclaredSpecializationVariantError` naming the code and the field (FR-027). This is what a resource calls after reading a row, so that the "which table does this row continue in" decision is written once in the framework and invoked explicitly by the developer — no resolution happens behind the developer's back, and nothing is inferred from a class name
- [ ] T033 [US4] Cover the resolution in `packages/aoa-action-machine/tests/action_machine/runtime/test_specialization_resolution.py`: a declared code resolves to its own class for every member of an axis; an undeclared code fails naming the value and the field; a code from another axis does not resolve; and the mapping is the one each extension declares, so removing a `Generalization` marker from one extension removes exactly that code
- [ ] T034 [US4] Cover the assignment contract in `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_assignment.py` on a real headline model: the object built for a resolved code goes into the field and reads back as the same object; an object of a class the union does not list is refused with `ValidationError`; a bare identifier is refused too, because pydantic tries to build one of the alternatives; and a field left empty reads as nothing rather than as a substituted type (FR-026, FR-028, FR-029)
- [ ] T035 [P] [US4] Pin the introspection and process-mining boundary in `packages/aoa-ocel/tests/test_ocel_specialization_boundary.py`, and make it discriminate: the extension object carried in the field is **not** reported as a foreign key by `BaseEntity.get_foreign_keys()` (the field holds an entity, not a relation container), while `_materialize_frame` on a frame whose root carries it returns exactly one object. Assert both halves — with only the second, the test passes whether or not anything reports it, which pins nothing
- [ ] T036 [US4] Run the checkpoint: `uv run --extra dev pytest packages/aoa-action-machine/tests/ packages/aoa-ocel/tests/ -v -k specialization`
**Checkpoint taken**: 32 tests named `specialization` in the Maxitor tree, the whole maxitor suite at 109, the action-machine suite at 2476, `ruff` clean, `npx tsc --noEmit` clean and the client built. The diagram was **rendered and read back**, because the container is the part no test can check: `examples/step_21_relations/02_specialization_erd.svg` and its `.dot` sit beside the worked example, and the DOT shows the three alternatives declared **inside** `subgraph "cluster_ex.VinylRecordEntity:pressing"` and nowhere else, the head outside it, and exactly one relation line with `arrowhead=vee` leading into the container. Seven properties of that picture are asserted by a script in this checkpoint: the cluster, the dashed frame, its label, one line, its arrowhead, the axis row, and the alternatives named in that row's type.

**Checkpoint**: all four stories are in. The failure modes the feature exists to remove are gone: no silent wrong table, no silent missing edge, no silently substituted type.

---

## Phase 7: The closing three steps (constitution, Principle VI)

**Purpose**: the constitution reserves **exactly these three tasks, in this order**, and no other task may absorb them.

- [ ] T037 [US1] [US2] [US3] [US4] Run the repository check to zero: `bash scripts/run_checks_with_log.sh` from the repository root; fix every remark it reports — none triaged away, none accepted as known, none left for later; review whatever `ruff check --fix` changed, because the run edits the code; the only two remarks that stay are the Vite chunk-size advisory and LangGraph's pending-deprecation warning
- [ ] T038 [US1] [US2] [US3] [US4] Write the documentation, after the code is settled: `docs/tutorials/step-21-relations.md` gains the specialization case with examples that actually ran (declaring the head and the extensions, the multi-axis shape, the runtime value, and the failure cases kept apart from the working ones); `docs/tutorials/step-26-maxitor.md` gains the ERD and full-graph view of the same model with the generated DOT and the rendered picture from T031; `docs/reference/intents-and-invariants.md` gains the rules under **Entity relations**, naming them for what they are — the first relation checks implemented in code, since the ownership matrix and the mandatory inverse documented there are still not enforced; `docs/reference/glossary.md` gains the terms; and `examples/step_21_relations/02_specialization.py` plus its notebook are the runnable form of every case, executed while they are written
- [ ] T039 [US1] [US2] [US3] [US4] Write the changelog last, as one article: `docs/CHANGELOG.md` gets a single readable piece about what this work created — a head row that continues in one of several tables, chosen by a value the model declares, what the diagram now shows, and what a developer has to know to use it — in plain words, without technical detail, without a per-file account and without a list of commits

## What is deliberately not in this spec

Four requests came up while the feature was being built. They are **two follow-up features, filed as issues, not tasks here**:

- **[#201](https://github.com/bystrovmaxim/aoa/issues/201)** — the demonstrator carries every access-cascade combination the diagram can draw: roles at each level, a hierarchy, `when=`, `guard=`, a declared object rule, two roles matching one operation, an early stop, a refusal that is an answer;
- **[#202](https://github.com/bystrovmaxim/aoa/issues/202)** — the stand: the demonstrator's generalization shapes, and both `dev.demo.aoa.run` and `dev.maxitor.aoa.run` in their own containers on one host, with the front end they must fit into and the deployment written down.

They belong together because the demo package is a **demonstrator, not a product**: its logic carries no meaning, it exists to produce the elements Maxitor draws. Issue #202 also records the two things this repository cannot settle alone — which access to use on that host, where another project's key already reaches it, and who owns the `aoa.run` zone. What they need — a container built from the repository rather than from PyPI, a client build inside it, two domains on one host, certificates, a deployment script — is a spec of its own, with its own acceptance ("open both domains and see every shape").

What stays **here** is the half that is this feature's own acceptance: T031 requires the generated DOT and the rendered diagram to be recorded, so the proof that a specialization reaches the picture lives in this spec. The stand proves every shape at once; this spec proves the shape it added.

Order agreed: this feature closes first, because a stand raised earlier would show a diagram without the axis this feature adds.

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** → the shared model; T012, T013 and T031 read it, so it is cheapest to write once, early
- **Phase 2 (Foundational)** → blocks every story; T002 is the containers, the marker and the second form of `Inverse`, and T003 the two errors
- **US1 (Phase 3)** → needs Phase 2 only; it is the MVP
- **US2 (Phase 4)** → needs US1's parser (T004); its rules are about declarations the parser produces
- **US3 (Phase 5)** → needs US1's graph node and edge (T006, T007, wired in T009); **does not need US2** and can run in parallel with it
- **US4 (Phase 6)** → needs US1's parsed axis (T004); does not need US2 or US3
- **Phase 7** → needs every story; T039 is last of all

### Within a story

- Implementation before its tests: T004→T011/T012, T014→T016/T017/T018, T023→T028/T029/T030, T032→T033
- **A cycle between two distinct classes cannot form, and three guards stand in front of the cycle rule.** Measured while writing T017: A names B and B names A, but the parser reads a class's code from the field pointing at **its own** head, so neither code is found and the two-sided comparison refuses the pair first. The cycle rule's reachable case is self-reference — a head naming itself — and that is what its test builds. The test for the mutual pair names the guard that actually fires instead of pretending the cycle rule caught it
- **The closure rule walked its own list.** It discovered the loaded entities by itself while every other rule used the set the pass had built, so a class a caller asked to be judged got every rule applied to it except this one. One pass, one list, and it is passed down
- **Mutuality has no check of its own, and that is a finding.** The rule says every alternative must be reachable from its head through a reverse field. Measured while writing T016: an alternative with no reverse field at all leaves the two-sided comparison naming an orphaned code, and so does an alternative whose reverse field does not point at this head — the parser cannot see it, so the head's code has no owner. A separate reachability rule never fired in any broken model, and it was removed rather than kept as a message nobody reads. Two further rules were found to overlap the same way ("declares no reverse field" and "declares no code"), and the reports are now one per cause instead of two per symptom
- **Generated models do not work for a sweep, and the reason is worth keeping.** The sweep wanted one shape with one part changed, which points at building the classes at test time. Measured twice — a plain subclass with rewritten `__annotations__`, then `create_model` — and both kept the annotation the class was created with, because pydantic caches the schema and `model_rebuild(force=True)` does not re-read the annotations. The cases are declared as classes, and the sweep asserts its own coverage against the design's rule table so a forgotten rule shows up as a missing case
- The pass and `@exclude_graph_model` had to agree about what a model is: the validator walks loaded `@entity` subclasses, and that walk reached classes the repository deliberately keeps out of the graph — test fixtures and samples — so a fixture written to be broken failed the build of every test that assembles one. Measured: 138 failures and 153 errors. A class marked `@exclude_graph_model` is not part of the model and is not judged; the walk skips it, and a test that wants a broken model judged passes the class in explicitly
- The exclusion is asserted as a **pair**, not as one absence: the axis reaches the system view and its reverse direction does not, in the same payload. Asserting only that generalization edges are absent would pass just as well if the axis had been dropped too — which is exactly what happens if its relationship is ever changed to `Generalization`. Checked by making that change: the axis disappears from the payload and the test fails on the first of the two assertions, naming what was lost
- The guard was first written the wrong way round: it removed the kind from the **payload** and expected a refusal, but the guard's whole job is to read the payload, so removing a row only removes the thing being guarded. The measured form is the opposite one — keep the emitter, take the registry away, and the load must die naming the kind, which is what a half-finished registration looks like to a user. Verified twice: removing both kinds from `known_edges` fails five of the ten tests, and the refusal names the kinds it did not recognise
- A column made **nullable** passed every test until one was added that reads `information_schema.columns`. The rows were right and the containment was wrong: a nullable property column lets a row through with the property missing, and the diagram would draw an axis with no partner field. Asserting the values a table holds is not the same as asserting what the table refuses to hold
- **`npm run build` does not type-check.** `vite build` transpiles and bundles, and it passed while `ErdGroup` was used but never imported — the mistake would have shipped as a runtime `undefined`. The client has `tsc` available, so `npx tsc --noEmit` is the check that actually reads the types, and it is what this task was verified with
- The container and the notation were checked by **rendering**, since the client has no test runner: the real payload goes through `buildDotSource` (bundled with the client's own esbuild), the DOT is rendered by the `@hpcc-js/wasm-graphviz` the client already depends on, and the SVG is read back for the frame and the labels. The DOT shows the three alternatives declared inside `subgraph "cluster_<axis>"` and nowhere else, the head outside, and exactly one relation line with `arrowhead=vee`
- The group contract is asserted without the pydantic wrapper. `JsonSchemaValue.define` builds a core schema whose validator calls `jsonschema.validate`, and the resulting `ValueError` is wrapped again by pydantic — so going through a `TypeAdapter` reports the **instance** and never the rule that refused it, which is exactly what a test about a contract needs to read. The tests validate against the schema object itself. Measured before switching: a `TypeAdapter` rejected even the correct payload, and the reason was invisible in the message
- The display spelling of an alternative belongs on the **edge**, not in a SQL string operation. The first attempt derived `Class (code)` inside the ERD query with `regexp_replace`, and it failed twice: DuckDB has no `transform`, and a regular expression cannot know that `Entity` is a suffix rather than part of a name. The edge now carries `labels` beside `alternatives` — same order, same length — where the class is in hand, and the ERD reads it. A property was added to the schema and to the storage table for it
- Two SQL mistakes are worth naming because both looked like "no data": counting alternatives inside the row's own group counted one every time (`COUNT(DISTINCT target_id) OVER (PARTITION BY …)` was needed, and it cannot sit in the same `SELECT` as a `GROUP BY`), and `field_node_id` was taken from the specialization edge, which points at an **entity**, not at the field's vertex — so the scalar row it was meant to displace stayed
- T024 turned out to have no subject: three node-type registries were checked — two in `list_node_types_action.py` and the client's `graph_node_disk_icons.ts` — and all three are keyed by node type. Specialization adds no node type, so nothing is declared there. The task is closed as a no-op with the check recorded, because a task silently dropped is indistinguishable from a task forgotten
- Registering `parent_entity` by the simple-table path would have built a table with no columns of its own, and the `edges` view would then export an **empty** payload for it — while the branch added in T020 requires four properties. The two registrations are therefore unlike each other on purpose: `entity_specialization` and `parent_entity` each get a table with their own columns, a view branch that builds the JSON from them, and a fill function, because a generalization that carries properties cannot travel through the path built for generalizations that carry none
- The guard was proved by removing the registration and rebuilding: the load died with `Unknown edge graph type(s): ['entity_specialization', 'parent_entity']`. Checking it *after* registering, as first written, proves nothing — a registered type is supposed to pass
- Two expectations were wrong when the schema test was written, and both are the kind that make a test look green for the wrong reason. **A refusal cannot be asserted by searching the message for the missing key**: `link` is a `oneOf`, so jsonschema reports the whole edge object, and the test would have been asserting on jsonschema's formatting. What ties a refusal to its mutation is the positive test beside it — the same payload unmutated validates. **A mutation that does not mutate has to be checked too**: the first attempt at breaking `additionalProperties` inserted the key into the `link_row` reference block, where it means nothing, and all twenty tests stayed green. The same break placed in the branch's own `properties` block did fail the test it was meant to, which is what makes the closure worth asserting
- The full-graph exclusion was checked rather than assumed, and the check was wrong the first time: the engine's own `to_json()` carries the `parent_entity` edges, which looks like the exclusion failing. It is not — the filter lives in Maxitor's `full_graph_action.py` (`WHERE relationship <> 'Generalization'`), so the edges reach the ERD and stay out of the system view, which is what the decision intended. A claim about what a downstream consumer strips is only a claim until the consumer is read
- Reading an extension's own code was about to exist in three places — the parser, the build validator and the graph edge — so the parser now owns both `read_reverse_declarations` and `read_declared_code`, and the validator's private copy was deleted rather than kept beside it
- The schema branch for `parent_entity` had to be written from scratch rather than reusing the three `parent_*` branches that already exist: those allow `maxProperties: 0` in their `properties` block, and an entity generalization has to name four things — the extension's field, the head's field, the code, and the head. Measured after the branch landed: a payload with every property accepted, and each of a missing property, an extra property, an unknown edge type and a wrong relationship refused
- Two rules behave differently from what the table implies, both measured while building the validator. **A repeated code on the head's side cannot be checked, because it cannot be written**: Python collapses `Literal["a", "a"]` to `Literal["a"]` before the marker sees it, and the de-duplicated literal yields fewer codes than alternatives, which the two-sided comparison refuses with its own message — so the head side is covered there, and no separate branch exists. **A repeated code across two classes is unreachable through a model**: the parser matches each code to a class, so the second class keeps no code and the comparison refuses the model first. The guard stays as a guard on the invariant, with its unreachability written where it lives
- T008 (excluding the field from the scalar columns) comes **before** T009 (wiring the vertex and the edges): the old question "is this a relation container?" answers no for a container-typed field, so until the exclusion lands the head would be both a column and a relation at once
- T010, the container and marker tests, may run anywhere after T002. It sits after the parser because the parser is what makes the capability usable, and the containers were exercised by hand while T002 was written
- The break-and-restore sweep (T018) depends on the whole validator (T014) and the coordinator hook (T015)
- Every test module that declares entity classes must mark them `@exclude_graph_model`
- T012 cannot assert that a payload **with** specialization passes `GRAPH_JSON_SCHEMA`: the schema is a checked-in document whose `link.oneOf` list does not carry the branch yet, and the failure is real — measured: `edges.22` is named when a fixture is left in the built graph. The branch lands in the phase that owns the schema, and the test that proves it belongs there: the entity inspector walks **every** loaded `BaseEntity` subclass, imported test modules included, so a deliberately broken model in a test file breaks the graph of every other test that builds one. Measured: six hundred tests failed across the suite until the exclusion was added
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
