# Examples — the six rewritten pages execute with this output

**Date**: 2026-10-24
**Source**: `examples/step_03_authorization_and_roles/`, rewritten in Procedure 7 (US5).

The four pages that taught the removed mechanism keep their numbers and move to the new names; the
two pages that taught the five words keep their names and now teach three. Each script was executed
with the repository's own environment and its actual output is recorded here and embedded in the
matching notebook.

## 02_object_rule (was 02_grant)

```text
EU manager: {'kind': 'allowed'}
US manager: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'EU_TEAM_ONLY'}
```

## 03_shared_object_rule (was 03_guard)

```text
amount 50: {'kind': 'allowed'}
amount 150: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'AMOUNT_LIMIT'}
```

## 07_three_answers

```text
check: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
run raises: AccessDenied
run verdict: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
```

## 13_cascade

```text
manager refused at: ACCESS_DECIDE
manager called: ['object']
stranger refused at: CHECK_ROLES
stranger called: []
```

## 17_branch_order (was 17_grant_fallback)

```text
US manager: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'EU_TEAM_ONLY'}
US admin: {'kind': 'allowed'}
```

## 22_reason_in_branch (was 22_reason_required)

```text
closed order: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'ORDER_ALREADY_CLOSED'}
open order: {'kind': 'allowed'}
```

## Suites

```text
uv run pytest packages/aoa-action-machine/tests/ -q  →  2994 passed
uv run pytest packages/aoa-demo/tests/ -q            →  79 passed
```

Both packages are green: every test module that named the removed mechanism is migrated, replaced
or deleted, and the demo's three actions draw the new shapes.
