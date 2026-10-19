# Quickstart — verifying the feature by hand

**Feature**: `specs/012-lifecycle-state-vocabularies` | **Date**: 2026-10-19

Five checks, in the order they become possible on the branch. Each names what to run and what must be seen; the shapes are in [contracts/](./contracts/).

## Prerequisites

- the repository's toolchain (`uv`, Python 3.12+), and `pnpm` for the Maxitor client;
- the branch `feature/issue-209-state-vocabularies`;
- a clean tree, so that a failing check belongs to the check, not to a half-applied edit.

## 1. A status is an object with fields

```python
from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary
```

Declare an axis class `class SalesOrderLifecycle(Lifecycle, StateVocabulary)` with two statuses as class attributes, each carrying a `sort_order` and a `color`, and `_template` in the same body. Run it as a script.

**Expected**

- `SalesOrderStates.NEW.code == "new"` and `.display_name == "New"` — the member is the object;
- iteration returns declaration order;
- `SalesOrderStates.by_code("new") is SalesOrderStates.NEW`;
- a status object of another axis named in `_template` is refused at the class statement, naming the status;
- `SalesOrderStateEntity(code="", display_name="X")` raises at construction.

## 2. The chain keeps the objects and the classification

Build the chain and ask it:

- `get_state_entity("payment_pending")` returns the object;
- `get_states()` still returns `StateInfo` entries whose `display_name` is the object's label;
- `get_initial_keys()` / `get_final_keys()` are the chain's, not the object's;
- the same status object used as `final` in one chain and `intermediate` in another builds in both chains.

**Command**

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_state_entity.py -v
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle.py -v
```

## 3. The graph row carries the label and the fields

Build a state row for the chain and print it:

- `label` is the human label, not the key;
- `id` and `type` are what they were before the change;
- `properties.attributes` holds every declared field, including `code` and `display_name`;
- a field marked `Field(exclude=True)` is absent;
- the row still validates against `GRAPH_JSON_SCHEMA`.

A minimal way to see it without the coordinator: construct the lifecycle graph node for a host class and print its `states[0].to_dict()`.

**Command**

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph_host/test_lifecycle_graph_node.py -v
```

## 4. Maxitor reads the same thing

Load a graph JSON containing the state row into the diagram store and ask for the FSM snapshot:

- `states[].display_name` is `"Payment pending"`, not `"payment_pending"`;
- `states[].attributes` carries the fields;
- the order is initial first, then `sort_order`;
- a graph without attributes still loads, and its DOT source is byte-identical to today's.

**Command**

```bash
uv run --extra dev pytest packages/aoa-maxitor/tests/test_get_lifecycle_finite_automaton_action.py -v
uv run --extra dev pytest packages/aoa-maxitor/tests/ -v
```

For the client:

```bash
cd packages/aoa-maxitor/client
pnpm install
pnpm run typecheck   # or the script the package defines
pnpm run build
```

The build must succeed with the optional `attributes` field; the generated DOT for a graph without attributes must not change.

## 5. The corpus did not move

After the migration, compare per-chain code sets and transition pairs against `main`:

- 32 declarations, every state code identical, every `(from, to)` pair identical;
- a repository scan finds no `.state("…"` and no `.to("…"` outside the removal tests.

**Commands**

```bash
git diff main -- packages/aoa-demo/src | grep -E '^[+-].*\.(state|to)\(' | head
uv run --extra dev pytest packages/aoa-demo/tests/ -v
uv run python examples/step_22_lifecycle/01_lifecycle.py
```

## 6. The closing run

```bash
bash scripts/run_checks_with_log.sh
```

Zero, apart from the two accepted remarks (the Vite chunk-size advisory and LangGraph's pending-deprecation warning).

## Adversarial breaks to perform before calling it done

Each restore afterwards; each must fail exactly one test.

| Break | Expected failure |
| --- | --- |
| remove the duplicate-code check from the mixin | the duplicate-code test |
| remove the `_template` membership check | the cross-axis test |
| drop `attributes` from the state row | the graph attributes test |
| drop the `attributes` column from the store | the FSM attributes test |
| change one demo code during the migration | the 1:1 corpus test |
| put the string branch back into `state()` | the `TypeError` refusal test |
| remove the `sort_order` ordering | the FSM order test |
| make the exclusion flag inherited | the "status type is not a model entity" test |
| require members on every subclass | the axis-subclass test |
