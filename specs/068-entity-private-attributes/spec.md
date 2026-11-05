# Feature Specification: An entity reads its private attributes

**Feature Branch**: `feature/issue-414-entity-private-attributes`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Issue #414, "Entity as DTO, beside step 1: an entity reads its private attributes", a fix found in #405, with case 13.1.

## Overview

A Pydantic model may keep **private attributes** (`PrivateAttr`): values that are not fields, never validated and never dumped. Pydantic keeps them in `__pydantic_private__` and finds them through its own `__getattr__`. `BaseEntity` defines its own `__getattr__` — it raises `FieldNotLoadedError` for a declared field a partial entity does not hold — and never hands other names to Pydantic, so an entity holds its private attribute but cannot read it. After this change every name that is not a declared field goes to Pydantic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a private attribute (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `OrderCoreEntity` with `_source: str = PrivateAttr(default="storage")`, **When** `OrderCoreEntity(id="o1")._source` is read, **Then** it is `"storage"` (case 13.1; Before: `AttributeError: 'OrderCoreEntity' object has no attribute '_source'`).
2. **Given** `OrderCoreEntity.partial(id="o1")`, **Then** `_source` reads `"storage"` too.
3. **Given** a declared field a partial entity does not hold, **Then** reading it still raises `FieldNotLoadedError`.
4. **Given** a name that is neither a field nor a private attribute, **Then** reading it still raises `AttributeError`.

## Requirements *(mandatory)*

- **FR-001**: `BaseEntity.__getattr__` MUST hand every name that is not a declared field to Pydantic's lookup.
- **FR-002**: The type check MUST pass without a comment that silences it and without a copy of Pydantic's lookup.

## Success Criteria *(mandatory)*

- **SC-001**: Case 13.1 gives its After output in a test; mypy reports no issue in `domain/entity.py`.

## Assumptions

- Measured on `main` at `4f22bccc0`: case 13.1 gives the Before of the issue.
