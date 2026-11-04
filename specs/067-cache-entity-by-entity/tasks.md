# Tasks: A collection is cached entity by entity

**Input**: `specs/067-cache-entity-by-entity/` — spec.md, plan.md, research.md

**Tests**: required. **Commits**: one phase = one commit; after a phase only its test files run.

- [ ] T001 [US1] Phase 1: `CacheLayout`, `@cache_entity_key`, the pairing at class creation, the entity fields at assembly; the `entity_key` node, `caches` edges to entity types, the dead-tag count; protocol 1.5 and its readers; tests `tests/action_machine/intents/cache/test_cache_entity_layout.py`.
- [ ] T002 [US2] Phase 2: the write of R2/R3; tests in `tests/action_machine/runtime/test_cache_entity_by_entity.py`.
- [ ] T003 [US3] Phase 3: the hit of R3; tests in the same file.
- [ ] T004 [US4] Phase 4: `get_entries` in `CacheCoordinator` and the how-to's store; a test counts the store's calls.
- [ ] T005 [US2] Phase 5: the machine test of 12.1 and 12.4 with Get, List, Update and Create actions; adversarial break.
- [ ] T006 Phase 6: versions.
- [ ] T007 Phase 7: `bash scripts/run_checks_with_log.sh` to zero.
- [ ] T008 Phase 8: tutorial step 8, the cache adapter how-to, an example with a notebook; Russian drafts.
- [ ] T009 Phase 9: one article and its Russian version.
