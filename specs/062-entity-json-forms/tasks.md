# Tasks: Every entity value has one JSON form

**Input**: `specs/062-entity-json-forms/` — spec.md, plan.md, research.md, data-model.md, contracts/json-forms.md, quickstart.md, checklists/

**Tests**: required — every case is a test (FR-010), and every fix has an adversarial break.

**Commits**: one phase = one commit. After a phase only that phase's test files run; an adversarial break runs against them alone.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Relations to ordinary entities (US1) — one commit

**Goal**: cases 1.1, 3.1–3.5.

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_relation_json_form.py packages/aoa-action-machine/tests/action_machine/domain/test_relation_container_protocols.py -q`

- [X] T001 [US1] Write `packages/aoa-action-machine/tests/action_machine/domain/test_relation_json_form.py`: entities Customer (UUID `id`, `orders: AssociationMany[Order]` with `Inverse`), Order (`customer: AssociationOne[Customer]` with `Inverse`, `lines: CompositeMany[Line]`), Line (`str` id), Tag (no `id`); tests of 3.1 (JSON dump of unloaded One and Many), 1.1 (loaded One with a partial customer), 3.2 (schema builds, `customer` closed with required `id` and `entity` by `$ref`, the recursive pair finite), 3.3 (read back from JSON and from a dict; not loaded), 3.4 (loaded zero rows vs not loaded), 3.5 (UUID ids for One and Many, typed after reading back; `"abc"` refused at `customer.id`; a no-`id` target takes `str` and `int`, refuses a float), a Python dump keeps the container, a container of another class refused, an unknown key refused, an undeclared field inside `entity` refused.
- [X] T002 Update `test_relation_container_protocols.py` case 1.1: the JSON dump of a loaded relation now gives the form `{'id': 'c1', 'entity': {'id': 'c1', 'name': 'Ann'}}`.
- [X] T003 Run T001–T002 and confirm the new tests fail on today's code.
- [X] T004 [US1] In `relation_containers.py`, implement R1 for ordinary targets in `BaseRelationOne/Many.__get_pydantic_core_schema__` (before step, closed typed dict with id schema from `handler.generate_schema`, target step publishing `handler.generate_schema(target)`, after step building a new container; JSON-mode serializer with the typed dict as return schema); keep `__get_pydantic_json_schema__` passing ordinary targets to the handler; update the module's data-flow notes and the AI-CORE blocks.
- [X] T005 Run the phase's tests; record the outputs.
- [X] T006 Adversarial breaks: open typed dict → unknown-key test fails; ids as `Any` → UUID test fails; `entities` ignored on read → loaded-zero test fails; restore after each.

---

## Phase 2: Dictionary references (US2) — one commit

**Goal**: cases 4.1–4.5 (4.1 and 4.2 through the adapters in Phase 4).

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_reference_forms.py packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association_schema.py packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_relation_containers.py -q`

- [X] T007 [US2] Write `test_dictionary_reference_forms.py`: 4.3 (a dict `{"id": "eur"}` in code, One; `[{"id": "usd"}, {"code": "eur"}]` and `[]`, Many); 4.4 (read back `model_dump_json()`; `{"code": "eur", "display_name": "Dollar"}` → `EUR` labelled `Euro`; validation schema `anyOf` the id object and the reference object; serialization schema the reference); 4.5 (JSON byte-identical to the reference built by `to_reference()`; a value's reference computed once — a counting probe; a reference returned by a dump changed by the caller does not change the next dump); a bare code still refused; a reference without `code` refused.
- [X] T008 Update `test_dictionary_association_schema.py` to the new messages where the JSON-only branch's wording was asserted; keep every refusal it tests.
- [X] T009 Run T007–T008 and confirm the new tests fail on today's code; measure 4.5 before.
- [X] T010 [US2] In `relation_containers.py`, replace the JSON-only/Python-only dictionary branches by one chain for every mode (R2), with `anyOf` input schemas; in `enum_entity.py`, compute the reference map once per dictionary after its catalogue is filled and serve new dicts from it in `_serialize_as_reference`; update AI-CORE blocks.
- [X] T011 Update the step-23 examples that assert the old messages or error types (`20_bare_code.py`, `23_missing_code.py`, `25_flat_fields.py`, `56_selection_transport.py`) and their notebooks with outputs from runs.
- [X] T012 Run the phase's tests and the example checks of `examples/step_23_dictionaries`; measure 4.5 after.
- [X] T013 Adversarial breaks: the dict input refused in Python mode again → the 4.3 tests fail; the stored reference returned as is → the mutation test fails; the reference recomputed per call → the counting test fails; restore after each.

---

## Phase 3: Lifecycle (US3) — one commit

**Goal**: cases 5.1 (schema part), 5.2–5.4.

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_json_form.py -q`

- [X] T014 [US3] Write `test_lifecycle_json_form.py`: JSON form with `properties`; Python dump keeps the lifecycle; schema builds with `code` enum `['draft', 'paid']`; `{"code": "draft"}` reads as `OrderLifecycle("draft")` from a dict and from JSON; `{"code": "shipped"}` refused naming the states; a bare string refused; 5.3 the status's own `model_dump()` unchanged; 5.4 identity after reading back and the changed list visible; a nullable lifecycle field round-trips `None`.
- [X] T015 Confirm T014 fails on today's code.
- [X] T016 [US3] In `lifecycle.py`, add `__get_pydantic_core_schema__` and `__get_pydantic_json_schema__` on `Lifecycle` (R3); update the module's notes and AI-CORE block.
- [X] T017 Run the phase's tests.
- [X] T018 Adversarial break: build the status from the stored properties instead of `cls(code)` → the 5.4 identity test fails; restore.

---

## Phase 4: Adapters end to end (US4) — one commit

**Independent test**: `uv run --extra dev pytest packages/aoa-fastapi-adapter/tests/test_fastapi_entity_fields.py -q`, then the MCP and LangGraph files below, each from the repository root.

- [X] T019 [P] [US4] `packages/aoa-fastapi-adapter/tests/test_fastapi_entity_fields.py`: an action whose Params hold a dictionary reference and an entity with a relation, and whose Result holds an entity with a relation, a reference and a lifecycle; `POST` with `{"currency": {"id": "eur"}}` → 200 (4.1) and the JSON forms in the response (5.1); `app.openapi()` builds; the alias field written as `itemId` (10.1).
- [X] T020 [P] [US4] `packages/aoa-mcp-adapter/tests/test_mcp_entity_fields.py`: `_validate_tool_request_kwargs({"currency": {"id": "eur"}}, PriceParams)` (4.2); `_serialize_result` writes the JSON forms and `item_id` (10.1).
- [X] T021 [P] [US4] Extend `packages/aoa-langgraph/tests/test_node_binding_entities.py`: the node's state receives entities with relations, references and a lifecycle (1.3); the alias field under `item_id`.
- [X] T022 Run the three files: all pass. Their cases failed before phases 1–3 (the Before outputs of 4.1, 4.2 and 5.1 in research.md), and the breaks of T006, T013 and T018 break them.

---

## Phase 5: Versions — one commit

- [X] T023 Raise `aoa-action-machine` in `pyproject.toml` and `uv.lock`; the adapter packages only if their code changed; `graph-builder check`.

## Phase 6: The closing check run — one commit if it changes anything

- [ ] T024 `bash scripts/run_checks_with_log.sh` to zero; correct every test or example the new id typing or input forms break (FR-011).

## Phase 7: Documentation — one commit

- [ ] T025 [P] Tutorial step 24 (relations): the JSON form of a relation, loaded and not, ids typed by the target, with a script and a notebook.
- [ ] T026 [P] Tutorial step 23 / how-to dictionary references: the input forms and the reference read back, with a script and a notebook.
- [ ] T027 [P] Tutorial step 25 (lifecycle): the JSON form and reading a status back, with a script and a notebook.
- [ ] T028 [P] Tutorial step 22 and the how-to on explicit entity fields: an entity as a Params/Result field now goes out and comes back; links to the sections above.
- [ ] T029 Example checks of the touched pages and examples; Russian drafts beside each page.

## Phase 8: Changelog — one commit

- [ ] T030 One article in `docs/CHANGELOG.md` and its Russian version in `docs/CHANGELOG.ru_draft.md`.

---

## Dependencies

- Phase 1 → Phase 2 (both edit `relation_containers.py`); Phase 3 independent; Phase 4 needs 1–3; Phases 5–8 follow in order.

## Implementation strategy

Phases 1–3 deliver the behaviour; Phase 4 proves it on every path; 5–8 are the tail. The pull request opens whole after Phase 8.
