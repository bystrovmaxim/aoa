# Quickstart: proving entity specialization works

Four scenarios, one per user story of [spec.md](./spec.md). Each is runnable against the repository as it is after the change, and each ends in an observable outcome rather than an assertion about internals.

## Prerequisites

```bash
# from the repository root
uv sync --extra dev
```

Nothing else: the capability adds no service, no store and no dependency.

## Scenario 1 — one field, five extensions, five targets (P1, SC-001)

Declare the head and the five extensions from `spec.md`, then build the graph and read the axis back:

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/intents/entity/ -v -k specialization
```

**Expected**: the machine builds; the resolved axis yields exactly five alternatives, five codes and one classifier; the head's field value carries `id` and `variant` and nothing else is needed to tell which table a row belongs to. **The falsifying run**: declare the same field with zero `Specialization` entries and rebuild — the build must fail with a named error, not produce an empty relation.

## Scenario 2 — break one rule, watch exactly that rule fire (P2, SC-002)

The sweep is the acceptance instrument: for each of the twenty build rules, break that one declaration, build, confirm the named error, restore, confirm the build passes.

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/ -v -k specialization_rule
```

**Expected**: twenty break-and-restore pairs, each failing with `SpecializationDeclarationError` naming the class, the field and the rule, and each restoring to a passing build with no other edit. **The falsifying run**: make a mistake the sweep does not cover — for example give two *different heads* the same extension class — and confirm it is caught by the multi-head rule rather than by whichever check happens to run first.

## Scenario 3 — the ERD shows one row and N relations (P3, SC-006)

```bash
# build the graph into DuckDB and ask the ERD payload for the domain
uv run --extra dev pytest packages/aoa-maxitor/tests/ -v -k "specialization or erd"
```

**Expected**: the head's `fields` list holds **one** entry named `<field> (by <classifier>)` whose type lists every alternative as `Class (code)`; the `relations` list holds **one** entry per axis, pointing at the axis container and labelled with the classifier, with the five alternatives inside that container; zero `FK -> ` rows for that field.

The rendering is checked from the built client and the opened diagram, not by a test — the client package has no test runner to run one in:

```bash
# 1. the built client carries the change
cd packages/aoa-maxitor/client && npm ci && npm run build

# 2. open Maxitor, choose the ERD workspace for the domain, and read the DOT
#    from the browser console: the ERD canvas receives it from buildDotSource()
```

**Expected**: the axis line carries `arrowhead=vee` and the five generalization lines carry `arrowhead=empty style=solid penwidth=1`; the head's field row reads `details (by event_type)`; in the browser the alternatives sit inside one container labelled with the axis, and the five generalization arrows end in a hollow triangle at the head's table, not in a filled head. Both the generated DOT and the rendered picture go into the documentation, which is what makes the rendering checkable without a runner.

**The falsifying run**: drop `entity_specialization` from the store's `known_edges` and reload — the whole load must abort with `Unknown edge graph type(s)`, which is the behaviour that makes a missing registration impossible to miss.

## Scenario 4 — a row whose code is not declared (P4, SC-008, SC-009)

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/runtime/ -v -k specialization
```

**Expected**: constructing a value with a code no alternative declares raises `UndeclaredSpecializationVariantError` naming the value and the field; constructing a value whose hydrated entity is not the class declared for its code raises `SpecializationDeclarationError`; neither produces an empty relation, and neither survives to a later read.

**The falsifying run**: swap the codes of two alternatives in the declaration only (leaving the extensions untouched) and rebuild — the build must fail on the code mismatch, because the head's code and the extension's code are compared rather than one being believed.

## Scenario 5 — nothing else moved (SC-005)

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/ -v
uv run --extra dev pytest packages/aoa-maxitor/tests/ -v
```

**Expected**: the existing entity-relation, lifecycle and ERD tests pass unchanged, and a model that declares no specialization produces the same graph payload it produced before the change. This is the run that proves the new axis is additive.

## The closing run

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: exit 0, with only the two accepted remarks in the log (the Vite chunk-size advisory and the LangGraph pending-deprecation warning). Anything else is fixed before the work is called done.
