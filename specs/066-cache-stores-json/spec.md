# Feature Specification: The cache stores JSON

**Feature Branch**: `feature/issue-410-cache-stores-json`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Issue #410, "Entity as DTO 7/8: the cache stores JSON", step 7 of 8 of #399, after #409 and #412, with its cases 9.1–9.3 and their real Before outputs. It covers what #84 asked for.

## Overview

The cache keeps an action's Result so that a repeated call returns it without running the action. Today it keeps the Python object itself and hands out that same object on every hit, so one caller's change is seen by every later one, and a store that keeps bytes, such as Redis, cannot be plugged in.

After this change the machine writes the Result to the store as UTF-8 JSON and reads it back into a new Result on every hit; a write refuses a Result whose JSON does not read back to the state that was written, naming the action and the field; and an entry that no longer reads with the current Result type is dropped and the pipeline runs.

## Clarifications

### Session 2026-11-05

The maintainer asked for the whole task without questions; the answers taken:

- Q: What does the store return from `get_entry` now? → A: a `StoredCacheEntry`: the payload bytes and the metadata (`pipeline_duration_ms`, `created_at`, `last_accessed_at`, `access_count`). `@cache_read` still receives a `CacheEntry`, whose `result` is the Result the machine read from those bytes.
- Q: Is the read-back compared by `==`? → A: by `observable_difference` (#409), so a lost loaded state or another declared object is a difference.
- Q: How is a difference reported? → A: by the top-level field it lies in; a scalar difference shows both values (`reads back as 20, but was 29`), any other shows the path the comparison gives.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every hit gets its own Result (Priority: P1)

A caller that changes the Result it received does not change what the next caller gets, and the store keeps only bytes.

**Independent Test**: Run a cached action twice, change the first Result between the runs, compare; read what the store holds.

**Acceptance Scenarios**:

1. **Given** `CachedListAction` returning `items=["a"]`, **When** the first Result's list is changed and the action runs again, **Then** the hit gives `(['a'], False)` (case 9.1; Before: `(['a', 'leak'], True)`).
2. **Given** a write, **Then** the store's `put` receives bytes, the Result's `model_dump_json()` in UTF-8, with the duration and the tags.
3. **Given** `@cache_read`, **Then** it receives a `CacheEntry` whose `result` is a new Result read from the bytes and whose metadata is the stored entry's; returning `None` still drops the entry and runs.

---

### User Story 2 - A Result that cannot be cached is refused at the write (Priority: P1)

**Independent Test**: Cache three Results that pass the build check and break rule 2.

**Acceptance Scenarios**:

1. **Given** a field `data: Any` holding a plain object, **When** the write runs, **Then** `CacheSerializationError` names `ReportAction.Result` and the field `data` and gives the serializer's error; nothing is stored (case 9.2).
2. **Given** a field serializer whose output its field does not accept (`count` → `"2 items"`), **Then** `CacheSerializationError` names `count`, the value and the error type `int_parsing`.
3. **Given** a field serializer that changes the value (`29` → `20`), **Then** `CacheSerializationError` says `field 'count' reads back as 20, but was 29`.
4. **Given** any of these, **Then** `CacheSerializationError` is a `CacheContractError`, and an action that does not cache is not affected.

---

### User Story 3 - An entry that no longer reads is dropped (Priority: P2)

**Independent Test**: Put bytes in the store that the current Result type refuses; run the action.

**Acceptance Scenarios**:

1. **Given** stored bytes the Result type refuses, **When** the action runs, **Then** the key is invalidated, `@cache_read` is not called, the pipeline runs, and the next run is a hit (case 9.3).

---

### User Story 4 - Rule 2 on a real hit (Priority: P1)

**Independent Test**: Through the machine, observe the bytes written and the object read on a hit, for a Result with relations, a lifecycle and a dictionary value.

**Acceptance Scenarios**:

1. **Given** such a Result, **When** it is written and hit, **Then** the hit's Result has no observable difference from the written one, and is another object.
2. **Given** the stored JSON with `entities` removed (the adversarial break), **Then** the test fails after the hit.

### Edge Cases

- A Result from `@on_error` is not written, as today; nothing is serialized for it.
- A write declined by `@cache_write` (`None`) serializes nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The machine MUST write `result.model_dump_json()` as UTF-8 bytes to the store and read a hit with `result_type.model_validate_json(payload)`; the store MUST NOT receive a Result.
- **FR-002**: `@cache_read` MUST receive a `CacheEntry` with the new Result and the stored metadata.
- **FR-003**: Before storing, the machine MUST read the bytes back and compare them with the Result by `observable_difference`; on a failed serialization, a failed read-back or a difference it MUST store nothing and raise `CacheSerializationError(CacheContractError)` naming the Result type, the field and the cause.
- **FR-004**: A hit whose bytes do not read MUST invalidate the key and run the pipeline without calling `@cache_read`.
- **FR-005**: The shipped `CacheCoordinator` and the how-to's example store MUST keep bytes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cases 9.1–9.3 give their After outputs in tests.
- **SC-002**: The real-hit test of US4 fails when `entities` is removed from the stored JSON.

## Assumptions

- Measured on `main` at `f9abb6d9e`: case 9.1 still gives `(['a', 'leak'], True)` with the declarations of #412.
