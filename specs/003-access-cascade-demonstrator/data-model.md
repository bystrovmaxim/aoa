# Phase 1 Data Model: Access cascade demonstrator

Everything below is a drawing fixture. No field carries business meaning; each element exists to produce one shape in Maxitor's diagram (FR-011).

## Domain

**`AccessCascadeDomain`** (`BaseDomain`, suffix `Domain`)

- `name = "access_cascade"`, `description` says the domain exists to demonstrate access-cascade shapes.
- Registered in the demo model via the two module lists (`model/build.py` and the mirror in `interchange_demo_coordinator.py`).
- No `events` attribute — event vocabulary is out of scope here (issue #95 territory).

## Roles

Role hierarchy is Python subclassing; the graph emits `parent_role` edges that Maxitor draws as chains.

| Role | Branch / level | Place in the hierarchy |
|------|----------------|------------------------|
| `CascadeSystemGateRole` | `SystemRole` — system level | engine sentinel, no parents |
| `CascadeStaffRole` | `ApplicationRole` — application level | chain root |
| `CascadeOfficerRole` | `ApplicationRole` | child of `CascadeStaffRole` |
| `CascadeLineLeadRole` | `ApplicationRole` | child of `CascadeOfficerRole` |
| `CascadeTraineeRole` | `ApplicationRole` | child of `CascadeLineLeadRole` (chain depth 4) |
| `CascadeDomainRole` | `BaseRole` — domain level | separate branch root |
| `CascadeDomainSpecialistRole` | `BaseRole` | child of `CascadeDomainRole` (chain depth 2) |

Validation rules (all enforced by the framework at class definition):

- Every class ends in `Role`; `name` and `description` are non-empty strings.
- The chains are acyclic by construction (single inheritance); the graph build refuses cycles.
- Descriptions name the shape: the level and the chain position, not a business duty.

## Operations

One action per cascade shape; `@meta` descriptions name the shape (FR-011). All are `BaseAction` subclasses with minimal Params/Result stubs — the pipeline body is a placeholder that returns the result.

| Action | FR | Declaration | Shape produced in the drawing |
|--------|----|-------------|-------------------------------|
| `RoleCheckAloneShapeAction` | FR-003 | `@check_roles(CascadeOfficerRole)` | a single role edge, nothing else |
| `WhenRefusalShapeAction` | FR-004 | `@check_roles(grant(CascadeOfficerRole, when=..., reason=...))` | a role edge whose condition can refuse after a match |
| `GuardRefusalShapeAction` | FR-005 | `@check_roles(CascadeOfficerRole, guard=..., guard_reason=...)` | a shared guard edge refusing everyone alike |
| `AccessDecideShapeAction` | FR-006 | `@access_decide(...)` answering on a real object | a declared object-rule node |
| `TwoPathMatchShapeAction` | FR-007 | `@check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)` | two independent role edges into one operation |
| `EarlyStopShapeAction` | FR-008 | `@check_roles(CascadeOfficerRole)` + `@access_decide(...)` with a probe counter | full declared cascade; the runnable test proves the object rule is unreached |
| `QuestionPathShapeAction` | FR-009 | same shape, description says it is the asked-about operation | a labelled element; the runnable test proves the refusal is an answer |

Validation rules:

- `when=`/`guard=` are synchronous `bool` functions with their reasons declared alongside (framework invariant).
- At most one `@access_decide` per operation, named `..._access_decide` (framework invariant).
- The probe counter in `EarlyStopShapeAction` is a module-level integer, reset by the test; it is a drawing fixture's proof instrument, not business state.

## Entities

**`CascadeBoundaryEntity`** (`BaseEntity`, suffix `Entity`) — FR-010

- One relation field declared with `NoInverse()` — the deliberate one-sided boundary.
- `= Rel(description=...)` carries a description naming the shape ("one-sided boundary for the drawing").
- No lifecycle, no other relations — the entity exists for the single boundary shape.

## Recorded artifacts

| Artifact | Location | Contents |
|----------|----------|----------|
| `access-shapes.dot` | `specs/003-access-cascade-demonstrator/contracts/` | Graphviz source of the drawn use-case diagram |
| `access-shapes.png` | `specs/003-access-cascade-demonstrator/contracts/` | rendered picture of the same diagram |

Produced once during implementation (Decision 8 in research.md), committed with the change (FR-013, SC-004).
