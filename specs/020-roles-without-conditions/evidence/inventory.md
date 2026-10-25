# Inventory — what still migrates, and what Procedure 2 already removed

**Date**: 2026-10-24
**Source**: research [R12](research.md) and [R13](research.md), re-derived by grep on the current tree.

The mechanism is `grant(`, `guard=`, `guard_reason`, `Grant`, `Gate.WHEN`, `Gate.GUARD`. Everything
below was found with that exact pattern, not from memory.

## Still in the tree — to migrate in Procedures 3–7

### Test modules (16)

Fourteen in `aoa-action-machine`:

```text
tests/action_machine/exceptions/test_access_denied.py
tests/action_machine/exceptions/test_access_undecided.py
tests/action_machine/graph/edges/test_role_graph_edge.py
tests/action_machine/graph/nodes/test_action_graph_node.py
tests/action_machine/graph/test_declared_reasons.py
tests/action_machine/intents/access_control/test_cascade.py
tests/action_machine/intents/access_control/test_cascade_decide.py
tests/action_machine/intents/access_control/test_gate_order.py
tests/action_machine/intents/access_control/test_roles.py
tests/action_machine/intents/access_control/test_verdict.py
tests/action_machine/intents/check_roles/test_check_roles_grant.py   (replaced by test_check_roles_removed_mechanism.py)
tests/action_machine/runtime/test_access_events.py
tests/action_machine/runtime/test_action_product_machine_check_access_decide.py
tests/action_machine/runtime/test_machine_decisions.py
```

Two in `aoa-demo`:

```text
tests/fastapi_mcp_services/test_cancel_order.py
tests/model/test_access_cascade_shapes.py
```

### Demo actions (3)

```text
src/aoa/demo/fastapi_mcp_services/actions/cancel_order.py
src/aoa/demo/model/access_cascade/actions/when_refusal_shape_action.py   → object_rule_refusal_shape_action.py
src/aoa/demo/model/access_cascade/actions/guard_refusal_shape_action.py  → forbidden_object_shape_action.py
```

### Example scripts (6) and notebooks (6)

```text
examples/step_03_authorization_and_roles/02_grant.py            + .ipynb
examples/step_03_authorization_and_roles/03_guard.py            + .ipynb
examples/step_03_authorization_and_roles/07_three_answers.py    + .ipynb
examples/step_03_authorization_and_roles/13_cascade.py          + .ipynb
examples/step_03_authorization_and_roles/17_grant_fallback.py   + .ipynb
examples/step_03_authorization_and_roles/22_reason_required.py  + .ipynb
```

### Documentation pages (3 + one ignored draft)

```text
docs/reference/glossary.md
docs/reference/intents-and-invariants.md
docs/tutorials/step-03-authorization-and-roles.md
docs/tutorials/step-03-authorization-and-roles.ru_draft.md   (git-ignored, rewritten beside the page)
```

## Already removed in Procedure 2

Four source modules (the mechanism plus what lost its last user with it):

```text
src/aoa/action_machine/intents/check_roles/grant.py
src/aoa/action_machine/intents/check_roles/reason_validation.py
src/aoa/action_machine/exceptions/access_condition_async_error.py
src/aoa/action_machine/exceptions/condition_reason_error.py
```

Two test modules (their only subject was deleted with them):

```text
tests/action_machine/intents/check_roles/test_reason_validation.py
tests/action_machine/exceptions/test_access_condition_async_error.py
```

## Cross-check against the research numbers

Research R13 named seventeen test modules that use the mechanism (fifteen in the package, two in
the demo). Of those, one — `test_reason_validation.py` — was already deleted in Procedure 2, leaving
sixteen, which is exactly the list above. `test_access_condition_async_error.py` never matched the
mechanism pattern (it names the exception, not the declaration) and is therefore counted separately,
also deleted. Nothing has appeared or vanished since the research except these two deletions.
