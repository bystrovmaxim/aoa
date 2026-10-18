# Adversarial evidence — US3, a second summary reported as a second summary

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T027 | **Date**: 2026-10-18

The rule: an operation answers once, so a second `@summary_aspect` is refused — and it is refused
with a message that names the two methods, not with the graph failure that used to stand in for it.

## What the tree said before the change

A probe action with two summaries, built into a machine, in a fresh interpreter
(`/tmp/two_summaries_machine.py`, deliberately outside the repository):

```text
InvalidGraphError -> Edge '@summary_aspect' from 'TwoSummariesProbeAction' references
missing target_node_id 'TwoSummariesProbeAction:second_summary'.
```

A developer reading that goes looking for a node they never wrote. Nothing in the message says the
operation declared two exit points — the actual defect — and nothing names the two methods.

## The break — the refusal silenced

```python
        if False:  # ADVERSARIAL BREAK: the duplicate is not refused
            names = ", ".join(sorted(method.__name__ for method in declared))
```

The same probe:

```text
InvalidGraphError -> Edge '@summary_aspect' from 'TwoSummariesProbeAction' references
missing target_node_id 'TwoSummariesProbeAction:second_summary'.
```

The confusing symptom is exactly what comes back when the refusal is removed, which is what makes
the refusal the thing the test pins rather than a cosmetic improvement on top.

The test file:

```bash
.venv/bin/python -m pytest \
  packages/aoa-action-machine/tests/action_machine/intents/aspects/test_duplicate_summary_aspect.py -q
```

```text
7 failed, 3 passed in 0.06s
```

The seven are the rule itself — the resolver's refusal, the message naming both methods and the
operation, the assembly moment, the `TypeError` catchability, and the three assertions that the
message and the graph name no missing node. The three that kept passing are the neighbours: one
summary is returned unchanged, no summary is an empty list, and no summary still raises
`MissingSummaryAspectError` — a different answer for a different situation.

## Restoration

```text
DuplicateSummaryAspectError -> TwoSummariesProbeAction declares more than one exit point
(first_summary, second_summary); an operation answers once.
```

```bash
.venv/bin/python -m pytest packages/aoa-action-machine/tests -q
```

```text
2606 passed in 14.18s
```

## The trap this task walked into, and the marker that avoids it

Declaring the two-summary fixture at module level in the test file broke **127 tests across the
suite**: the graph inspector walks every loaded `BaseAction` subclass, so a single class with two
summaries poisons assembly for every other test in the same process — the same reason
`test_missing_check_roles.py` runs its fixture in a subprocess.

The fixtures now carry `@exclude_graph_model`, which keeps them out of the shared graph while
leaving them fully usable through the resolver and through an explicitly constructed
`ActionGraphNode`. That is the marker's purpose, and it is the difference between a test that
checks a rule and a test that breaks the suite.

## One expectation that did not need changing

`T027` said `test_aspect_intent_resolver.py` "currently asserts a list of two" and would need
updating. It asserts a list of **one** — `[ChildAction.build_result_summary]` — so the new refusal
never fires there and the file is untouched. Recorded here because the task text was wrong about it,
and a task that quietly edits a test it did not need to edit is a task that hides its own mistakes.
