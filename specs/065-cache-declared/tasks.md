# Tasks: The cache is declared like an access check

**Input**: `specs/065-cache-declared/` — spec.md, plan.md, research.md

**Tests**: required. **Commits**: one phase = one commit; after a phase only its test files run.

## Phase 1: Declarations (US1, 11.1, 11.6) — one commit

- [X] T001 [US1] Write `packages/aoa-action-machine/tests/action_machine/intents/test_cache_declarations.py`: description, suffix, `async`, names and order, annotations, `@context_requires` above instead of under; one of a kind naming both; not inherited; types at assembly; old names refused naming the replacement; `BaseAction` has none of the four methods.
- [X] T002 [US1] Rewrite `tests/action_machine/runtime/test_action_product_machine_cache.py`, `test_action_product_machine_cache_invalidation.py`, `tests/action_machine/model/test_base_action_cache_hooks.py` and the cache part of `test_emission_rules.py` with declarations: hit, `ctx` in the key, `@cache_read` returning `None`, invalidate before write, `@on_error` neither writes nor invalidates.
- [X] T003 Confirm they fail on today's code.
- [X] T004 Create `intents/cache/` (R1): decorators, signature, resolver, marker; `BaseAction` loses the four methods and checks one of a kind and old names in `__init_subclass__`; the machine calls the declarations (R3).
- [X] T005 Run the phase's tests; adversarial breaks of plan phase 1.

## Phase 2: Pairing (US2, 11.2) — one commit

- [X] T006 [US2] Tests: key alone, write alone, read without the pair refused at class creation with the message of 11.2; invalidate alone accepted.
- [X] T007 Implement in `validate_cache_declarations`; run; adversarial break.

## Phase 3: Tag types (US3, 11.4) — one commit

- [ ] T008 [US3] Tests: `tags=` on write and invalidate; a returned tag of an undeclared type and one without a type raise `CacheContractError` naming action and tag; empty invalidate tags and a non-entity type refused at declaration.
- [ ] T009 Implement R4; run; adversarial break.

## Phase 4: The graph (US4, 11.3, 11.5) — one commit

- [ ] T010 [US4] Tests: `Cache` nodes with kind and description; `caches` and `invalidates` edges; a dead invalidation and a dead tag refused at build; the graph's JSON valid against 1.4; Maxitor loads `Cache` nodes and the new edges.
- [ ] T011 Implement R5 in AOA and R6: protocol 1.4 and its copies, the graph builder's schema and fixture, Maxitor's store; run; adversarial breaks.

## Phase 5: Graph files and versions — one commit

- [ ] T012 `graph-builder write`; raise every level that changed; `uv lock`.

## Phase 6: Closing check run — one commit if it changes anything

- [ ] T013 `bash scripts/run_checks_with_log.sh` to zero.

## Phase 7: Documentation — one commit

- [ ] T014 Tutorial step 8, the reference of intents and invariants, the how-to on a cache adapter, the glossary, and the examples that cache, with notebooks; Russian drafts.

## Phase 8: Changelog — one commit

- [ ] T015 One article and its Russian version.
