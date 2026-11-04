# Tasks: The cache stores JSON

**Input**: `specs/066-cache-stores-json/` — spec.md, plan.md, research.md

**Tests**: required. **Commits**: one phase = one commit; after a phase only its test files run.

## Phase 1: Bytes (US1, 9.1) — one commit

- [X] T001 [US1] Write `packages/aoa-action-machine/tests/action_machine/runtime/test_cache_stores_json.py`: case 9.1; `put` receives bytes; `@cache_read` receives the new Result with the stored metadata.
- [X] T002 Implement R1 in `cache_entry.py` and `cache_coordinator.py`, and the machine's encode and read; update the tests that read `CacheEntry.result` from the store.

## Phase 2: The write's read-back (US2, 9.2) — one commit

- [X] T003 [US2] Tests: the three kinds raise `CacheSerializationError` with the messages of R2, nothing stored; it is a `CacheContractError`.
- [X] T004 Implement R2 and `exceptions/cache_serialization_error.py`.

## Phase 3: Stale entries (US3, 9.3) — one commit

- [ ] T005 [US3] Tests: unreadable bytes → invalidated, pipeline run, `@cache_read` not called, next run a hit.
- [ ] T006 Implement R3.

## Phase 4: Rule 2 on a real hit (US4) — one commit

- [ ] T007 [US4] `tests/action_machine/runtime/test_cache_hit_round_trip.py` with a recording store (R4); adversarial break.

## Phase 5: Versions — T008 · Phase 6: Closing check run — T009 · Phase 7: Documentation — T010 · Phase 8: Changelog — T011

- [ ] T008 Raise `aoa-action-machine`; `uv lock`.
- [ ] T009 `bash scripts/run_checks_with_log.sh` to zero.
- [ ] T010 Tutorial step 8, the how-to on a cache adapter and its example and notebook; Russian drafts.
- [ ] T011 One article and its Russian version.
