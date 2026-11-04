# Tasks: An entity tells the truth in Python

**Input**: `specs/060-entity-truth-in-python/` — spec.md, plan.md, research.md, data-model.md, contracts/entity-api.md, quickstart.md

**Tests**: required — every case of #405 is a test (FR-010), and every fix has an adversarial break.

**Commits**: one phase = one commit. After a phase only that phase's test files run; an adversarial break runs against them alone. Nothing is committed without the maintainer's instruction.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Relation containers (US1, US2) — one commit

**Goal**: a container never passes itself off as its entity, and copies and pickles as a container (cases 1.1–1.5).

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_relation_container_protocols.py packages/aoa-langgraph/tests/test_node_binding_entities.py -q`

### Tests first

- [X] T001 [P] [US1] Write `packages/aoa-action-machine/tests/action_machine/domain/test_relation_container_protocols.py` with tests for: case 1.1 (JSON dump of an entity with a loaded `AssociationOne` raises `PydanticSerializationError` naming the container, never `{}`); case 1.2 (`model_dump()` of `PricesCoreEntity(primary=CompositeOne(id="eur"))` returns `{'primary': CompositeOne(id='eur', loaded)}`); a dunder name on a loaded container raises `AttributeError`; `order.customer.name` still reads `'Ann'`; an unloaded container still raises `RelationNotLoadedError` for an ordinary name; a name with one leading underscore is still forwarded.
- [X] T002 [P] [US2] Add to the same file tests for case 1.4 (`copy.deepcopy(loaded)` and `order.model_copy(deep=True).customer` are `AssociationOne` with the same id and a copy of the entity, for a One and a Many container) and case 1.5 (`copy.copy`, `copy.deepcopy` and a `pickle` round trip of a loaded and an unloaded container give an equal container that still refuses assignment).
- [X] T003 [P] [US1] Write `packages/aoa-langgraph/tests/test_node_binding_entities.py`: case 1.3 — `_run_action_node` with an action whose Result holds `PriceCoreEntity(id="p1", currency=CompositeOne(id="eur"))` returns `{'price': {'id': 'p1', 'currency': CompositeOne(id='eur', loaded)}}`.
- [X] T004 Run T001–T003 and confirm each fails on today's code with the Before output of #405.

### Implementation

- [X] T005 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py`, make `BaseRelationOne.__getattr__` raise `AttributeError` for a name that starts and ends with `__` before it looks at the entity; keep every other name forwarded.
- [X] T006 [US2] In the same file add to `BaseRelationOne` and `BaseRelationMany` `__reduce__` (rebuilds through the constructor from `type(self)`, the id(s), the entity(ies) and the loaded state; `copy.copy`, `copy.deepcopy` and `pickle` all use it), each with a one-line docstring; update the classes' AI-CORE blocks to state the copy and forwarding contract.
- [X] T007 Run the phase's tests (T001–T003): all pass.
- [X] T008 Adversarial breaks, one at a time, against the phase's test files only: forward dunder names again in T005 → the 1.1–1.4 tests fail; remove `__reduce__` → the deep-copy tests of 1.4 and the copy, deepcopy and pickle tests of 1.5 fail; restore after each.

**Checkpoint**: show the diff; commit only on instruction.

---

## Phase 2: Partial entities (US3, US4) — one commit

**Goal**: a partial entity holds only what was loaded, reads nothing it did not load, runs no code of an unloaded field, and reports what it holds (cases 2.1–2.3); equality unchanged (FR-009).

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_partial_loading.py packages/aoa-action-machine/tests/action_machine/domain/test_entity_partial_getattr.py -q`

### Tests first

- [X] T009 [P] [US3] Write `packages/aoa-action-machine/tests/action_machine/domain/test_entity_partial_loading.py` with tests for: case 2.1 (`currency: str = "RUB"` unloaded → `FieldNotLoadedError` on read, absent from `model_dump()` in both modes, `is_field_loaded` False); case 2.3 (a factory `lambda data: data["id"].upper()` → `partial()` returns an instance with nothing loaded; a counting factory runs 0 times for `partial(id="o1")`); a partial with every field equals the full entity and reports every field loaded; a full entity still applies its defaults.
- [X] T010 [P] [US4] Add case 2.2 to the same file: `partial(id="o1").model_copy(update={"total": 2.0})` reports `total` loaded and reads 2.0, while a field still unloaded raises `FieldNotLoadedError`.
- [X] T011 [P] [US3] Add a test that pins the construction against Pydantic: a partial instance has exactly the given keys in `__dict__`, `model_fields_set` equal to them, `__pydantic_extra__` None and the class's private defaults.
- [X] T012 Run T009–T011 and confirm each fails on today's code with the Before output of #405.

### Implementation

- [X] T013 [US3] In `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py`, rewrite `BaseEntity.partial()` to create the instance without `model_construct`, setting `__dict__` to the given fields only, `__pydantic_fields_set__` to their names, `__pydantic_extra__` to None and `__pydantic_private__` to the class's private defaults (research R1); remove `_partial_instance` and `_loaded_fields`.
- [X] T014 [US3] In the same file make `__getattr__`, `is_field_loaded` and `get_field_value` decide by presence of the field in the instance's `__dict__`: a declared field that is absent raises `FieldNotLoadedError` with the loaded field names; update the module docstring and the AI-CORE block of `BaseEntity` to the new contract.
- [X] T015 [US3] Revisit `packages/aoa-action-machine/tests/action_machine/domain/test_entity_partial_getattr.py`: the test that expected a generic `AttributeError` for a declared field missing on a non-partial instance now expects `FieldNotLoadedError` (an `AttributeError`); keep its intent, do not weaken it.
- [X] T016 [US3] Update the docstring example in `packages/aoa-action-machine/tests/support/domain_model/entities.py` if it no longer matches (it still matches: no change).
- [X] T017 Run the phase's tests only — the files T009–T011 and T015 wrote or changed: all pass. The other tests that build partial entities (`test_entity_introspection.py`, `test_specialization_container.py`) run in the closing check run (T020).
- [X] T018 Adversarial break against the phase's test files only: build `partial()` through `model_construct` again → the 2.1 and 2.3 tests fail; restore.

**Checkpoint**: show the diff; commit only on instruction.

---

## Phase 3: Versions — one commit

- [X] T019 Raise the version of each level that changed in its `version.toml` (`packages/aoa-action-machine`; `packages/aoa-langgraph` only if its code changed — tests alone do not count, per `docs/how-to/run-the-checks.md#versions`), and rebuild the graph files with `graph-builder` if they change.

---

## Phase 4: The closing check run — one commit if it changes anything

- [ ] T020 Run the checks this machine can run, the example checks included, take every remark to zero, and fix what they find in this work; the two accepted remarks of the constitution stay.

---

## Phase 5: Documentation — one commit

- [ ] T021 [P] Update `docs/tutorials/step-22-entity.md` (partial entities: an unloaded field with a default is not readable, nothing of an unloaded field runs, `model_copy(update=...)`), explanations from #401 section 4.2, examples run with outputs from the runs; add a script and notebook under `examples/step_22_entity/` for every new case.
- [ ] T022 [P] Update `docs/tutorials/step-24-relations.md` (a container is never its entity: dumps, copies and pickles), explanations from #401 section 4.1, with a script and notebook under `examples/step_24_relations/`.
- [ ] T023 [P] Update `docs/how-to/dictionary-references.md`: its statement that Python-mode `model_dump()` retains the wrappers gets an example that runs, as a script and a notebook under `examples/how_to/`.

---

## Phase 6: Changelog — one commit

- [ ] T024 Write one article in `docs/CHANGELOG.md`: what changed for a reader of entities, in plain words, without per-file detail.

---

## Dependencies

- Phase 1 and Phase 2 touch different files and are independent; they are done in order 1 → 2 so each is its own commit.
- Phases 3–6 follow both, in this order (constitution VI).
- Inside a phase, tests first; T004 and T012 must show the failures before the implementation starts.

## Parallel opportunities

- T001, T002, T003 (different files or independent tests); T009, T010, T011; T021, T022, T023.

## Implementation strategy

Phase 1 alone is a complete fix of cases 1.1–1.5; Phase 2 alone of 2.1–2.3. Both ship in one pull request with the tail, which opens whole.
