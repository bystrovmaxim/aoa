# Specification Quality Checklist: A resource is a database, and the model knows no store

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- This is a framework change: its users are developers, so the spec names the framework's own declarations (`@entity`, `@entities`, `PostgresPool`, `ResourceEntitiesError`), as the repository's earlier specs do. Those declarations are the subject of the change, not an implementation detail.
- Every requirement is demonstrated by a user story: FR-001–FR-004 and FR-008 by story 1, FR-009–FR-013 by story 2, FR-006–FR-007 by story 3, FR-014 by story 4, FR-015 by story 5; FR-005, FR-016–FR-018 cross the stories and their own verification.
- Acceptance scenarios do not yet name the exact refusal message for every case; the error text of `ResourceEntitiesError` is fixed by story 2's scenario 3, the other refusals name the class, the argument or the requirement they refuse.
- Five points were clarified in the session: one entity may be listed by two resources, every resource kind may declare `@entities`, a subclass of a listed class is refused while a partial answer of that class passes, "comes in a wrapper" means the resource's own public methods are wrapped rather than a proxy, and a class repeated in one `@entities` list is refused. Three more were settled by default and recorded in the Assumptions: `ResourceEntitiesError` is a runtime `TypeError`, an empty `@entities` declares a resource that returns no entity, and mapping keys appear in a refusal path as `[key]`.
- Scope is bounded in the Clarifications (writes are not bounded by domain; Maxitor's views and one transaction across two resources are excluded) and the change waits on #485, #486 and gnomon#66, all named.
