# Quickstart — How to Prove This Feature Works

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-24

A validation guide, not an implementation. Each scenario names what to run and what the run must
show. Contracts it checks: [role declaration](contracts/role-declaration.md),
[answers and order](contracts/decision-and-cascade.md),
[graph projection](contracts/graph-projection.md).

## Prerequisites

```bash
cd /Users/bystrovmaxim/PythonDev/aoa
uv sync --extra dev          # once per environment
```

The repository's own runner is `bash scripts/run_checks_with_log.sh`; it appends to
`archive/logs/check-all.txt` and is the closing gate, not a per-scenario tool. Use the scoped
commands below while working.

## S1 — An accepted declaration builds and matches

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/intents/check_roles/ \
  packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py -v
```

**Expected**: every accepted form in [the declaration contract](contracts/role-declaration.md#accepted-forms)
has a passing case; the caller-side table is asserted for `GuestRole`, `AnyRole`, a bare role, a
tuple and several positional roles; silenced caller roles grant nothing; `UNUSED` is still refused
where it is declared and `DEPRECATED` still warns.

## S2 — A removed declaration fails where it is written

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_check_roles_removed_mechanism.py -v
```

**Expected**: `guard=`, `guard_reason=` and `when=` are refused at class definition with a message
containing `@access_decide`; `from aoa.action_machine.intents.check_roles import grant` raises
`ImportError`; a leftover condition object passed positionally is refused with the same teaching
text. No warning-only path exists, and no deprecated member survives.

## S3 — A sentinel keeps its meaning inside a choice

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py -v -k "sentinel or choice or any_role"
```

**Expected**: `@check_roles(GuestRole, CustomerRole)` allows a caller with no roles and a caller
holding `CustomerRole`; `@check_roles(AnyRole, CustomerRole)` requires at least one role that is
not silenced; a declaration naming one role twice behaves as that one role and produces one graph
edge.

## S4 — The object rule refuses, on both paths

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/runtime/test_action_product_machine_check_access_decide.py \
  packages/aoa-action-machine/tests/action_machine/runtime/test_machine_decisions.py -v
```

**Expected**: the same answer from `machine.run(...)` and from
`machine.check_access_decide(...)`; a locked object answers `Refused("ORDER_LOCKED")` with gate
`ACCESS_DECIDE`; a foreign object answers `FORBIDDEN_OBJECT`; a rule that returns a `bool`, `None`
or a string answers `Undecided` naming `ACCESS_DECIDE`, never `Allowed`; a rule that raises is
`Undecided` too.

## S5 — Three words, and no fourth

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/intents/access_control/ \
  packages/aoa-action-machine/tests/action_machine/exceptions/ -v
```

**Expected**: `len(Gate) == 3`; every answer produced by the cascade carries one of the three;
`Refused(gate="WHEN")` and `Refused(gate="GUARD")` fail validation as an unknown value, including
when they arrive through `model_validate` from stored data; a failing step produces `Undecided`
naming its own word with the cause kept privately.

## S6 — The graph says roles, and points at the rule

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/graph/ -v
```

**Expected**: one `@check_roles` edge per distinct role with empty exported properties and no
condition data; an action node with no `guard`/`guard_reason`; an `AccessDecide` node present
exactly when the operation declares a rule, carrying its description and required-context
companions.

## S7 — The demo and the teaching pages

```bash
uv run --extra dev pytest packages/aoa-demo/tests/ -v
uv run examples/step_03_authorization_and_roles/02_object_rule.py
uv run examples/step_03_authorization_and_roles/03_shared_object_rule.py
uv run examples/step_03_authorization_and_roles/17_branch_order.py
uv run examples/step_03_authorization_and_roles/22_reason_in_branch.py
```

**Expected**: the three demo actions build and answer as [research.md](research.md#r11--the-demo-package)
describes; each rewritten page runs to completion and prints what the page records, and its
notebook shows the same steps with the same output.

## S8 — Adversarial mutations

Each mutation is applied in a temporary copy or a scratch fixture, never in the user's working
source, and each must fail its targeted check while a valid neighbouring control passes.

| Mutation | Expected detection |
| --- | --- |
| re-add `@check_roles(grant(Role))` | the declaration test for removed keywords fails |
| delete `@check_roles` from an operation | the mandatory-role refusal fires at assembly |
| require a `SILENCED` caller role | the role gate still refuses |
| add `@access_decide` to a `GuestRole` operation that allows | the same operation now refuses |
| read a module-level value inside `@access_decide` | the code-isolation check of issue #247 — **not in the tree yet**, so until it lands the same mutation is verified by review with a recorded search and the result says which of the two produced it |

## S9 — The closing gate

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: no errors. Two remarks are accepted and are not acted on — the Vite chunk-size
advisory and LangGraph's pending-deprecation warning. Ruff, mypy across all eight packages, pylint,
vulture, Radon and the test suite of every package, including `aoa-demo`, must pass.

## What this guide does not cover

It does not run the examples' notebooks cell by cell; that belongs to the documentation task and is
verified by executing the notebooks with the same environment. It does not assert Maxitor's
rendering beyond the payload tests named in [the graph contract](contracts/graph-projection.md).
