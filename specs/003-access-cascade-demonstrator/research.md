# Phase 0 Research: Access cascade demonstrator

All NEEDS CLARIFICATION items from the Technical Context were resolved against the existing codebase. Findings, with decisions.

## Decision 1: The fixtures live in a dedicated `access_cascade` domain group

- **Decision**: new module group `packages/aoa-demo/src/aoa/demo/model/access_cascade/` with `access_cascade_domain.py`, `roles/`, `actions/`, `entities/`, registered by editing the two existing module lists (`model/build.py` and its mirror `interchange_demo_coordinator.py`).
- **Rationale**: FR-014 (dedicated domain, existing content untouched). Sibling domains already follow this layout; the two registration lists are the only entry points that must change.
- **Alternatives considered**: spreading fixtures across existing domains (violates FR-014, muddies the drawing diff); a new package (unnecessary — the demo model already groups domains under one package).

## Decision 2: Role levels and hierarchy come from the existing role branches

- **Decision**: three branches, all drawn by the interchange graph's `parent_role` edges:
  - **System level**: one `SystemRole` subclass (`CascadeSystemGateRole`) — engine sentinel branch.
  - **Application level**: a 4-deep subclassing chain under `ApplicationRole`: `CascadeStaffRole` → `CascadeOfficerRole` → `CascadeLineLeadRole` → `CascadeTraineeRole` (satisfies FR-002 "several levels deep").
  - **Domain level**: `CascadeDomainRole` (`BaseRole`) with one child, `CascadeDomainSpecialistRole` — a second, shorter chain.
- **Rationale**: role hierarchy in AOA is Python subclassing (MRO); `RoleChecker` uses `issubclass`; the graph emits `parent_role` edges that Maxitor draws as inheritance chains.
- **Alternatives considered**: string role names (not typed — fails framework invariants); flat roles (no chain — fails FR-002).

## Decision 3: One operation per cascade shape, names say the shape

- **Decision**: seven actions, each carrying the shape in its class name and in its `@meta` description (FR-011):

| FR | Action fixture | Declaration that produces the shape |
|----|----------------|--------------------------------------|
| FR-003 | `RoleCheckAloneShapeAction` | `@check_roles(CascadeOfficerRole)` alone |
| FR-004 | `WhenRefusalShapeAction` | `@check_roles(grant(CascadeOfficerRole, when=..., reason=...))` |
| FR-005 | `GuardRefusalShapeAction` | `@check_roles(CascadeOfficerRole, guard=..., guard_reason=...)` |
| FR-006 | `AccessDecideShapeAction` | `@access_decide(...)` on a real object |
| FR-007 | `TwoPathMatchShapeAction` | `@check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)` — one match through the hierarchy, one through the domain branch |
| FR-008 | `EarlyStopShapeAction` | `@check_roles(CascadeOfficerRole)` + `@access_decide` whose probe counter proves it never ran |
| FR-009 | `QuestionPathShapeAction` | same declaration, asked via `machine.check_access_decide` — refusal as an answer |

- **Rationale**: each shape must be findable by sight in the drawing; a name that contains the shape plus a description that names it satisfies FR-011 without inventing business meaning.
- **Alternatives considered**: one action with many aspects (mixes shapes, breaks FR-011 and the edge cases); realistic store-like names (would claim business meaning the demonstrator must not have).

## Decision 4: `when=` and `guard=` are trivial, reason-carrying predicates

- **Decision**: each condition is a synchronous function returning a constant `False` (refusing) with a declared reason naming the shape, e.g. `when=lambda params: False, reason="shape: WHEN refuses although the role matched"`. The `guard=` fixture uses `guard=lambda params: False, guard_reason="shape: GUARD refuses every caller alike"`.
- **Rationale**: the framework invariant requires `reason=` alongside `when=` and `guard_reason=` alongside `guard=`; a constant predicate is the only honest "fixture" — there is no business logic to express.
- **Alternatives considered**: conditions that read `params` (would imply business meaning); omitting reasons (violates the declaration invariant at import time).

## Decision 5: The early stop is proven by a probe, not by the drawing

- **Decision**: `EarlyStopShapeAction` runs as a caller who fails `CHECK_ROLES`; its `@access_decide` increments a module-level counter. The test asserts the refusal names `CHECK_ROLES` and the counter is zero — the object rule was declared (visible in the drawing) but provably not reached (FR-008).
- **Rationale**: the drawing shows declarations, not executions; a refusal's stopping point is a runtime fact. A probe counter is the smallest honest proof and matches the issue's "provably not reached".
- **Alternatives considered**: asserting on exception text only (does not prove the later gate never ran); drawing a special "stopped" edge (no such edge exists in the graph model).

## Decision 6: The question path is an element labelled by its description, proven by a run

- **Decision**: `QuestionPathShapeAction`'s `@meta` description says it is the asked-about operation (the drawn label); the runnable proof calls `machine.check_access_decide` and asserts a refusal answer — no exception, and no aspect ran. This is the "both" answer from Clarification Q1.
- **Rationale**: the drawing carries labels (descriptions) already; the answer-not-exception property is behaviour, proven by running.
- **Alternatives considered**: a Maxitor change to draw a special "question" mark (out of scope — the assumption states gaps in drawing belong to Maxitor, and none is needed here).

## Decision 7: The `NoInverse` extreme is one entity with a one-sided relation

- **Decision**: `CascadeBoundaryEntity` carries one relation field declared with `NoInverse()` — the deliberate one-sided boundary FR-010 asks for.
- **Rationale**: the ERD draws inverse markers; a `NoInverse()` field is exactly the "boundary worth drawing" shape, and it requires no partner entity.
- **Alternatives considered**: an entity pair with `Inverse(...)` (that is the ordinary shape, not the extreme).

## Decision 8: DOT and picture are recorded like the entity-specialization precedent

- **Decision**: during implementation, build the Maxitor client and the demo, open the use-case diagram for the `access_cascade` domain, capture the DOT source and a rendered PNG, and commit both as `specs/003-access-cascade-demonstrator/contracts/access-shapes.dot` and `access-shapes.png`. The rendering is checked by eye — the client package has no test runner (same reasoning as `specs/002-entity-specialization/quickstart.md`).
- **Rationale**: Clarification Q2 chose `contracts/`; the 002 precedent already established "DOT + picture into the documentation" as the checkable form.
- **Alternatives considered**: a pytest that renders PNG (no headless renderer in the repo); committing only the DOT (the issue demands a rendered picture too).

## Decision 9: No Maxitor or framework changes in the primary scope

- **Decision**: the fixtures only. The interchange graph already emits `check_roles` edges, `parent_role` edges and the `access_decide` node that Maxitor's DuckDB queries read.
- **Rationale**: the spec's assumption — the drawing gap, if any, belongs to Maxitor, not to this feature's fixtures.
- **Risk and fallback**: if a shape fails to draw after the fixtures land (e.g., the use-case diagram does not surface `parent_role` chains), the gap is reported and fixed in Maxitor as a separate, follow-up issue — not absorbed silently into this feature.

## Decision 10: Naming stays inside the framework's suffix grammar

- **Decision**: all new classes end in `Action`, `Role`, `Domain` or `Entity`; shape words appear in the name itself; module files follow the snake_case convention of the demo package.
- **Rationale**: suffixes are enforced by `__init_subclass__`/decorators; self-describing names satisfy FR-011.
- **Alternatives considered**: prefix `Demo*` (no added value, longer names).
