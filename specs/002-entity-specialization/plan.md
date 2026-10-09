# Implementation Plan: Entity specialization — one field, N extension tables, chosen by a classifier

**Branch**: `feature/issue-199-entity-specialization` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-entity-specialization/spec.md`

## Summary

A new relation **axis** beside ownership: one entity field names N alternative target entities, each with a variant code, plus the classifier field on the head whose value selects among them. Every extension declares its own reverse field and repeats its code; the build compares the codes and refuses every broken declaration with a named error. The head's field yields N targets instead of one, the field's runtime value carries both the id and the variant, and the graph publishes a dedicated `entity_specialization` edge so Maxitor can draw one field row naming all alternatives and N generalization relations (extension → head). The work lives inside `packages/aoa-action-machine`; the other touches are the Maxitor store's edge registry, the ERD payload SQL, and the Graphviz builder in the Maxitor client (see [research.md](./research.md)).

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"`; the engine already uses PEP 695 generics such as `class BaseRelationOne[T]`)

**Primary Dependencies**: pydantic v2 (`BaseEntity` / `model_fields`, already the engine's model base), the engine's own graph coordinator and JSON-schema module — no new dependency is introduced

**Storage**: none. The engine stores and generates nothing: it validates the declaration, publishes the mapping, and carries the variant at runtime. Turning the mapping into a table constraint belongs to a graph consumer (spec, Out of scope)

**Testing**: pytest, per package (`packages/aoa-action-machine/tests/action_machine/**`, `packages/aoa-maxitor/tests/**`), with the break-and-restore sweep of SC-002 as the acceptance instrument

**Target Platform**: the engine library plus Maxitor's store, ERD payload and browser ERD renderer; no endpoint and no wire format of its own

**Project Type**: a library change inside a monorepo (`packages/aoa-action-machine`) plus a consumer change (`packages/aoa-maxitor`), closed by the repository-wide check run

**Performance Goals**: the build gains one global pass over entity nodes; no new measurable target, and no I/O is added to the engine or to the load path

**Constraints**: the field's declared type position carries no target, so the field is recognised by its markers — every place that today decides "is this a relation container" needs an explicit branch or the field is silently dropped (the failure mode the feature exists to remove); the graph schema is a hand-maintained JSON document whose `link.oneOf` list, `$defs` and `relationship` enum are checked in tests; the Maxitor store aborts the whole load on an unregistered node or edge type (`_assert_no_unknown_graph_types`) and needs five registration sites per new type, since its `nodes`/`edges` views are unions that each gain a branch; the ERD field-row contract is `additionalProperties: false` and enforced at runtime, so a new key on the row is a schema change and not a detail; the Maxitor client has no test runner at all, so the rendering is proved by the generated DOT and the rendered diagram recorded in the documentation rather than by a new client test; the full-graph payload excludes edges by the single predicate `relationship <> 'Generalization'`, which the new generalization edges reuse deliberately; one existing marker gains a second form on the head (`Inverse` naming the partner field alone, without the target type) and its `target_entity` becomes optional, which is an addition to a public declaration and not a new marker; the classifier is a marker **object**, because a bare keyword cannot stand inside `Annotated`; the field parameterises a container with the union of the alternatives, the codes are a `Literal` on both sides, and the build compares the two sets in both directions, so neither copy of the mapping is the authority; two documented relation rules (the ownership matrix, the mandatory inverse) are **not** implemented today, so the new checks are the first relation checks in code and must not silently claim to enforce them; one pre-existing defect measured on the way — `entity_relation_intent_resolver` loses every relation when `get_type_hints` cannot resolve an annotation — is recorded in [research.md](./research.md) and deliberately left to an issue of its own, because fixing it would widen this capability into a module and a test set it does not otherwise touch; `bash scripts/run_checks_with_log.sh` green at the end

**Scale/Scope**: 2 new container types, 1 new marker type, 1 new intent resolver row type, 1 new graph edge kind plus 1 new field node kind, 2 exceptions, 1 global build pass, 1 schema branch, 5 store registration sites × 2 new types in Maxitor, 3 backend ERD changes plus 1 client rendering change, 1 pinned process-mining boundary, 39 tasks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only |
| II. English in commits, in git and in code | Every new file: module header, docstrings, comments, tests, commits — English | PASS — planned |
| III. Module headers | Each new module opens with its repository-relative path comment, a `Name — purpose.` first line, and the 79-column `═` sections the codebase uses | PASS — planned |
| IV. AI-CORE blocks | Every new public class carries `ROLE` and `CONTRACT`, plus `INVARIANTS` where the type has them; no block in a module docstring or on a method | PASS — planned |
| V. Short docstrings | Every new class, function and method gets its one-line docstring, ending with a period, identifiers in double backticks | PASS — planned |
| VI. Check run, documentation, changelog | Exactly three closing phases, in that order, and no other phase absorbs them | PASS — phases 12, 13, 14 |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is the last step, and every remark it reports is fixed | PASS — phase 12, and the tail remark check |

No violations, so **Complexity Tracking** stays empty.

**Re-check after Phase 1 design**: the design adds no dependency, no new package, and no new module outside the folders named below; the only public surface added is the declaration vocabulary (two markers, one value type, one edge kind) and one exception. Every gate above still passes, and no exception has to be justified.

## Project Structure

### Documentation (this feature)

```text
specs/002-entity-specialization/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: the declarations, the rules, the runtime value
├── quickstart.md        # Phase 1 output: how to prove it works
├── checklists/
│   └── requirements.md  # Spec quality checklist
├── contracts/           # Phase 1 output: the surfaces this capability fixes
│   ├── declaration-surface.md
│   ├── graph-payload.md
│   └── runtime-value.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── domain/
│   │   ├── specialization_containers.py            # NEW: Specialization[T], Generalization[T], Classifier
│   │   ├── relation_markers.py                     # Inverse gains its second form
│   │   ├── entity.py                               # get_foreign_keys: one explicit branch
│   │   └── exceptions.py                           # + SpecializationDeclarationError
│   ├── intents/entity/
│   │   ├── entity_specialization_intent_resolver.py  # NEW: the axis row and its parser
│   │   └── entity_intent_resolver.py               # + resolve_entity_specializations
│   ├── graph/
│   │   ├── validators/
│   │   │   └── entity_specialization_validator.py  # NEW: the 20 build rules, one global pass
│   │   ├── edges/
│   │   │   ├── entity_specialization_graph_edge.py # NEW: head → alternatives, with codes
│   │   │   ├── entity_field_graph_edge.py          # scalar edges must not swallow the field
│   │   │   ├── entity_graph_edge.py                # unchanged: ownership relations keep ASSOCIATION
│   │   │   └── (the generalization branch of the schema, `$defs` near line 886)
│   │   ├── nodes/
│   │   │   └── entity_specialization_field_graph_node.py  # NEW: the one field row
│   │   ├── core/node_graph_coordinator.py          # build(): run the specialization pass
│   │   └── graph_json_schema.py                    # 3 new $defs + 2 link.oneOf branches
│   └── ...
└── tests/action_machine/
    ├── domain/                                     # markers, the value type, the exception
    ├── intents/entity/                             # the axis parser and its refusals
    ├── graph/                                      # the the build rules, the schema, the payload
    └── runtime/                                    # hydration, mismatch, undeclared code

packages/aoa-maxitor/
├── src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py  # 5 registration sites × 2 new types
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action.py     # the ERD payload SQL (row, relation, neighbor clause)
├── src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py  # the widened field-row contract
├── src/aoa/maxitor/model/diagrams/actions/list_node_types_action.py   # the new vertex type in both registries
└── client/src/lib/buildDotSource.ts                                   # hollow triangle + the row label

packages/aoa-ocel/tests/test_ocel_specialization_boundary.py           # the process-mining boundary, pinned

docs/tutorials/step-21-relations.md, docs/tutorials/step-26-maxitor.md,
docs/reference/intents-and-invariants.md, docs/reference/glossary.md,
docs/CHANGELOG.md, examples/step_21_relations/, examples/step_26_maxitor/   # phase 13, 14
```

**Structure Decision**: the new edge kinds are `entity_specialization` (head → alternative, `relationship="Association"` like every other entity relation, so it stays in the full graph) and `parent_entity` (extension → head, `relationship="Generalization"`, which the existing predicate keeps out of the full graph). The parent-family schema entries today allow **no** properties (`maxProperties: 0`), so the generalization branch gains its own `$defs` entry with the four property keys, and the `link.oneOf` list gains two branches. The capability is the engine's concern, so the new modules live in the folders the relation feature already uses — `domain` for the declaration vocabulary and the runtime value, `intents/entity` for the resolver, `graph/edges`, `graph/nodes`, `graph/validators` for the interchange. `graph/validators/` is the one new folder, and it holds a single module: the build rules are a pass of their own over the whole entity set, not a per-node concern, and putting them beside the per-node edge builders would hide that. Maxitor changes only where an edge type or an ERD row is registered, because the store rejects unknown types by design and the ERD needs the union row and the relation notation.

## Complexity Tracking

No constitution violations to justify.
