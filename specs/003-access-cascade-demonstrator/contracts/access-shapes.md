# Contract: what the access-shapes drawing must show

The demonstrator is judged by looking (FR-013, SC-001). This file is the contract between the fixtures in `packages/aoa-demo` and the recorded diagram in this directory. For each shape: what a viewer must be able to see, which interchange-graph element carries it, and the requirement it proves.

| # | Shape | What the drawing must show | Carrying graph element | Requirement |
|---|-------|----------------------------|------------------------|-------------|
| 1 | Role check alone | an operation node with exactly one role edge and no condition, guard or object rule | `check_roles` edge to one role | FR-003, SC-001 |
| 2 | Role condition (`when=`) | an operation whose role edge carries a condition that can refuse although the role matched | `check_roles` edge with the grant's condition attached | FR-004, SC-001 |
| 3 | Shared guard (`guard=`) | an operation whose shared limit refuses every caller alike, distinct from the role condition | `check_roles` edge with the operation's guard attached | FR-005, SC-001 |
| 4 | Declared object rule | an operation with a visible object-rule node, answered on a real object inside the run | `access_decide` node/edge | FR-006, SC-001 |
| 5 | Role levels | a system role, an application role and a domain role all present | role nodes of the three branches | FR-001, SC-001 |
| 6 | Hierarchy | an inheritance chain several levels deep — a role connected to its ancestors, not floating alone | `parent_role` edges | FR-002, SC-001 |
| 7 | Two matching paths | one operation reached by two roles through different branches | two `check_roles` edges into one action node | FR-007, SC-001 |
| 8 | Early stop | the full cascade declared; the runnable test (not the picture) proves the later stages were not reached | the same edges as shapes 1–4; proof lives in `packages/aoa-demo/tests/model/test_access_cascade_shapes.py` | FR-008, SC-001 |
| 9 | Refusal as an answer | an element labelled as the asked-about operation; the runnable test proves the refusal returns as an answer without running the pipeline | the operation's label (description) plus the `check_access_decide` proof in the tests | FR-009, SC-001 |
| 10 | `NoInverse` boundary | an entity whose relation is deliberately one-sided, drawn as a boundary | `NoInverse()` relation field on `CascadeBoundaryEntity` | FR-010, SC-001 |

## Artifact manifest

Recorded evidence in this directory:

- `access-shapes.dot` — the generated Graphviz source of the use-case diagram for `AccessCascadeDomain` (shapes 1–9), built by the Maxitor client's own `buildDomainUseCaseDotBundle` from the payload of `GetDomainUseCaseDiagramAction`.
- `access-shapes.svg` — the same diagram rendered by the same Graphviz WASM engine the client uses, with the role actor asset.
- `access-shapes-erd.dot` — the generated Graphviz source of the ERD slice for the domain (shape 10), built by the client's own `buildDotSource` from the payload of `ListEntitiesAction`.
- `access-shapes-erd.svg` — the same ERD slice rendered by the WASM engine.
- `access-shapes.png` / `access-shapes-erd.png` — browser captures of the two diagrams from the built Maxitor client (the client package has no test runner; the PNG is the look-at evidence, the same way `specs/002-entity-specialization` records its picture).

## Known gaps found while recording

- **The system branch needs an edge to draw.** The use-case closure pulls roles only through `@check_roles` edges, so an unconnected role is invisible. The `SystemRoleEdgeShapeAction` fixture (added during the recording of this contract) names `CascadeSystemGateRole` so the system level appears in the diagram.
- **The ERD payload does not carry `has_inverse`.** `ListEntitiesAction` selects no inverse marker, so a `NoInverse` boundary renders like an ordinary one-way relation row (the visible boundary here is the self-loop with its cardinalities, not a distinct style). Marking one-sided boundaries in the ERD is a Maxitor follow-up, out of scope for this feature's fixtures (per the spec's assumption).

## Honesty rule

Every label in the drawing comes from the elements' descriptions, and every description names the shape (FR-011). A viewer must never read a label as a business claim — there is none.
