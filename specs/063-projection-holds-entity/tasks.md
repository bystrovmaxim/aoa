# Tasks: A projection holds the entity

**Input**: `specs/063-projection-holds-entity/` — spec.md, plan.md, research.md

**Tests**: required (FR-009). **Commits**: one phase = one commit; after a phase only its test files run.

## Phase 1: Projections (US1–US3) — one commit

- [X] T001 [US1] Write `packages/aoa-action-machine/tests/action_machine/domain/test_projection_holds_entity.py`: 6.1 from a full entity, a partial and a dict; JSON out only the projection's fields; reading a field outside raises `FieldNotLoadedError`; a partial without a required field refused naming it; 6.2 Params from a dict and JSON give a partial entity with attribute and `["id"]` reads; a value the schema accepts and the field type refuses is refused; an entity of another class refused; 6.3 a schema naming `secret` refused at declaration; Python dump gives the projection's fields; a `| None` projection keeps `None`.
- [X] T002 Update `test_entity_schema_pydantic.py` and `aoa-demo/tests/model/test_entity_projection_samples.py`, which compare the value to a dict, to compare its fields.
- [X] T003 Confirm T001 fails on today's code.
- [X] T004 Create `domain/partial_fields.py` (R1) and move the reader of #407 there; `relation_containers.py` uses it.
- [X] T005 `entity_schema_marker.py`: the validator of R2 and the property check of R3; notes and AI-CORE.
- [X] T006 Run the phase's tests; adversarial breaks of plan phase 1.

## Phase 2: A field typed by the entity carries a full one (US4) — one commit

- [X] T007 [US4] Write `test_entity_field_takes_full.py`: bare, `| None`, `list[...]` refuse a partial with the message of R4; a full one accepted; a dictionary value unaffected.
- [X] T008 Confirm it fails; implement R4 in `model/full_entities.py`, used by `BaseParams` and `BaseResult`, with the projection marker's `holds_partial_entity`; run the phase's tests and the package; adversarial breaks.

## Phase 3: The graph edge (US5) — one commit

- [X] T009 [US5] Write `test_entity_typed_field_graph_edge.py`: bare, `| None`, `list[...]`, a dictionary type each give an `entity_schema` edge; a projection unchanged; a non-entity field none.
- [X] T010 Confirm it fails; implement R5 in the two field nodes and `entity_schema_graph_edge.py`; run; adversarial break.

## Phase 4: Graph files and versions — one commit

- [X] T011 `graph-builder write` if the files change; raise `aoa-action-machine` (and any other level the diff touches); `uv lock`.

## Phase 5: Closing check run — one commit if it changes anything

- [X] T012 `bash scripts/run_checks_with_log.sh` to zero; correct what relied on a dict projection.

## Phase 6: Documentation — one commit

- [ ] T013 Steps 17 and 18: a projection holds the entity, on output and input, with a script and a notebook; step 22: a field typed by the entity carries a full one, a projection for a part; Russian drafts.

## Phase 7: Changelog — one commit

- [ ] T014 One article and its Russian version.
