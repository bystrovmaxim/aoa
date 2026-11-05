# Implementation Plan: An entity belongs to one resource, and its relations stay inside it

**Branch**: `feature/issue-469-entity-belongs-to-resource` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

## Summary

`@entity` takes `resource=` instead of `domain=`; the entity's domain is read from the resource's `@meta` (R1, R2). A new class-level pass refuses every link and every shared state type across resources when the model is built (R3, R6). The graph gets `EntityResourceGraphEdge` and a node-level check in `NodeGraphCoordinator.build`, and is written as protocol 1.6 (R4, R5). Every declaration in the tests, examples, demo and docs moves to a resource (R7, R8).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14)

**Primary Dependencies**: Pydantic 2 (entities), the graph layer of `aoa-action-machine`; protocol schema copied from bystrovmaxim/gnomon `graph/1.6.json`

**Storage**: N/A — the saved graph file `packages/aoa-demo/graph.json`

**Testing**: pytest per package; `tests/scripts`; examples run in CI jobs of their own

**Target Platform**: library

**Project Type**: library (monorepo of seven packages)

**Performance Goals**: the class-level pass is linear in entity fields, like the three passes beside it

**Constraints**: every check in AOA (gnomon describes, Maxitor reads); the schema copy byte for byte

**Scale/Scope**: ~1 024 `@entity` declarations to move (R7)

## Constitution Check

- **I** — authorised for this issue: the whole path, the pull request and the merge after every check passes; one phase = one commit.
- **II** — English in code, commits and the pull request; no tool footer, no `Co-Authored-By`.
- **III–V** — new modules open with their path, a docstring with `PURPOSE` and `ARCHITECTURE / DATA FLOW`; new public classes carry an AI-CORE block; every function a one-line docstring.
- **VI** — the tail is three tasks: the closing check run, the documentation (every case as a script and a notebook, each run), the changelog as one article; the pull request opens whole.
- Check run — after each phase only that phase's tests; CI runs the closing run.

No violation. Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/069-entity-belongs-to-resource/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/entity-decorator.md
└── tasks.md (+ tasks.ru_draft.md)
```

### Source Code

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── intents/entity/entity_decorator.py          # resource=, checks (R2)
├── intents/entity/entity_intent_resolver.py    # resolve_resource_type, domain via the resource (R1)
├── domain/exceptions.py                        # EntityResourceError (R3)
├── domain/lifecycle.py                         # Lifecycle.state_type() (R6)
├── graph/validators/entity_resource_validator.py  # new class-level pass (R3, R6)
├── graph/edges/entity_resource_graph_edge.py   # new edge (R4)
├── graph/edges/domain_graph_edge.py            # entity domain from the resource
├── graph/nodes/entity_graph_node.py            # resource edge
├── graph/core/node_graph_coordinator.py        # pass + node-level check + 1.6 (R4, R5)
└── graph/graph_json_schema.{json,py}           # 1.6 copy (R5)
packages/aoa-action-machine/tests/…             # new tests + every declaration moved
packages/aoa-{fastapi-adapter,mcp-adapter,langgraph,ocel}/tests/…
packages/aoa-demo/src/aoa/demo/model/…           # resources, moves, removals (R8); graph.json
tests/scripts/test_schema_copies.py
examples/…, docs/…, README.md, docs/CHANGELOG.md, version.toml files
```

## Phases (one phase = one commit)

1. **`@entity(resource=...)`** (2.1–2.3, 2.5, 2.6): decorator, resolver, domain edge from the resource. Tests: every row of the contract's declaration table; the domain read from the resource. Adversarial: drop the excluded-class check → the `BaseStorage` test fails; read the domain from the entity again → the 2.6 test fails.
2. **The model build refuses links across resources** (2.4): `EntityResourceError`, `validate_entity_resources` in `build`. Tests: association, aggregation, composition (each side), inverse side, specialization, generalization, dictionary field, shared state type, a self-relation and a same-resource model accepted. Adversarial: skip the lifecycle group → its test fails; skip generalization targets → its test fails.
3. **The graph** (2.5): `EntityResourceGraphEdge`, node field, node-level check, schema 1.6, `schema_version`. Tests: the edge row; the domain edge's target; schema validation of a built graph; zero and two edges refused; a relation edge across resources refused (nodes built by hand past the class pass); the copy's `$id`/SHA-256. Adversarial: write two edges → the count test fails; drop the node check → the hand-built test fails.
4. **The demo** (R8): resources, moves, `CurrencyEnumEntity` into Billing, 23 associations removed, spread by meaning, `CatalogDenseLifecycle` split; demo tests updated. Tests: the demo's tests.
5. **Examples and tests**: every declaration moved (R7). Tests: every package's test suite of the files touched; the examples that changed run.
6. **Graph files and versions**: `graph-builder write`, `version-gate`.
7. **The closing check run**, taken to zero, the example checks included.
8. **Documentation**: tutorial steps 21–25, the how-to pages that declare entities, `docs/reference/intents-and-invariants.md`, `README.md`; new cases as scripts and notebooks with their real output.
9. **Changelog**: one article.

Phases 1–3 leave the other test files red until phases 4–5 move them; each phase runs only its own tests, as the constitution's check run says.

## Complexity Tracking

None.
