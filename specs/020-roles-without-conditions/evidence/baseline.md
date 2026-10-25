# Baseline — the three affected packages at Procedure 1

**Date**: 2026-10-24
**Commit**: `90dd83e502a0129bd92a8636296efbdb085a9862` (`main`, includes #262)

## What the tree is at this measurement

- HEAD is `main` at `90dd83e5`; the branch `feature/issue-248-check-roles-without-grant-guard` is
  fast-forwarded to the same commit, so the base already carries #262 (four entity validators, the
  `specs/021-*` planning set, 68 code/example files).
- On top of that commit sits the uncommitted **Procedure 2** surgery — 6 deletions and 15
  modifications in `packages/aoa-action-machine` plus the spec/plan/tasks adaptations. The baseline
  below is therefore measured with the role layer already stripped and the migration debt still
  unpaid: this is the designed intermediate state, not a defect of the change.
- The other five packages (`aoa-ocel`, `aoa-otel`, `aoa-fastapi-adapter`, `aoa-mcp-adapter`,
  `aoa-langgraph`) are not baselined here; nothing in this change reaches them, and T029 covers them.

## Command

The first T001 command combined the three package directories in one `pytest` invocation. That
broke Maxitor's import mode (`ModuleNotFoundError: No module named 'tests...'`), so the baseline is
measured the way `scripts/run_checks_with_log.sh` runs it — one package at a time:

```text
uv run --extra dev pytest packages/aoa-action-machine/tests/ -q
uv run --extra dev pytest packages/aoa-demo/tests/ -q
uv run --extra dev pytest packages/aoa-maxitor/tests/ -q
```

## Results

### aoa-action-machine — collection aborted, 0 tests ran

```text
10 errors during collection; Interrupted
```

The ten modules that fail to import all do so because their declarations or imports still use the
removed mechanism; migrating them is Procedure 3–5:

```text
tests/action_machine/graph/edges/test_role_graph_edge.py
tests/action_machine/graph/test_declared_reasons.py
tests/action_machine/intents/access_control/test_cascade.py
tests/action_machine/intents/access_control/test_cascade_decide.py
tests/action_machine/intents/access_control/test_gate_order.py
tests/action_machine/intents/access_control/test_roles.py
tests/action_machine/intents/check_roles/test_check_roles_grant.py
tests/action_machine/runtime/test_access_events.py
tests/action_machine/runtime/test_action_product_machine_check_access_decide.py
tests/action_machine/runtime/test_machine_decisions.py
```

### aoa-demo — collection aborted, 0 tests ran

```text
2 errors during collection; Interrupted
```

```text
tests/fastapi_mcp_services/test_cancel_order.py
tests/model/test_access_cascade_shapes.py
```

Both fail because the three demo actions they exercise still declare `grant(...)`/`guard=`; that is
Procedure 7 (US5) work.

### aoa-maxitor — green, unchanged

```text
154 passed, 1 skipped, 1 xfailed
```

Maxitor never named the removed mechanism; the rewrite of the action-machine source leaves its
payload unchanged, which is what the plan's R10 asserted.

## Reading

A failure in `aoa-action-machine` or `aoa-demo` is attributable to this change only when it is **not**
one of the twelve collection errors listed above — those are the migration debt paid in Procedures
3–7. Maxitor is the control: it must stay green through the whole feature.
