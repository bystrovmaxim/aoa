# Baseline evidence — what the tree does before the change

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T001 | **Date**: 2026-10-18

**Base commit**: `90b2cdeb` (`docs(spec-kit): the aspect declaration contract, from the issue to the task list`), the tip of `feature/issue-193-aspect-decorator-signature-invariants`, itself on `main` at `c61bdfe6`.

**Environment**: Python 3.12.12 (`.venv/bin/python -VV`), repository root as working directory.

Three probes, each with the command that produced it and its output verbatim. They are what makes the change a before/after rather than an assertion.

---

## P1 — a renamed, reordered, untyped declaration is accepted

The probe lives at `evidence/probes/p1_renamed_declaration.py` and is re-runnable after the change.

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/probes/p1_renamed_declaration.py
```

```python
@summary_aspect("S")
async def renamed_summary(self, s, p, b, c):
    return None


@regular_aspect("R")
async def reordered_aspect(self, box, params, state, connections):
    return {}
```

Output:

```text
summary accepted: renamed_summary | is coroutine fn: True
regular accepted: reordered_aspect | is coroutine fn: True
[exit 0]
```

**What it proves**: neither decorator looks at the names or the order. The engine will hand over `(self, params, state, box, connections)` by position, so `s` receives the parameters object and `p` receives the state — the declaration says one thing, the call does another, and nothing objects.

---

## P2 — a summary's answer is handed back unchecked

The probe lives at `evidence/probes/p2_unchecked_answer.py` and is re-runnable after the change.

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/probes/p2_unchecked_answer.py
```

The action declares `BaseAction[ParamsStub, ResultStub]`; its single summary returns a plain `dict` and carries no return annotation.

```python
@meta(description="Summary returns a dict instead of its Result", domain=ProbeDomain)
@check_roles(GuestRole)
class JunkAction(BaseAction[ParamsStub, ResultStub]):

    @summary_aspect("Return a dict, not a Result")
    async def junk_summary(self, params, state, box, connections):
        return {"not": "a result"}
```

Output:

```text
answer type : dict
answer value: {'not': 'a result'}
is ResultStub: False
[exit 0]
```

**What it proves**: `AspectExecutor.execute_summary` resolves the operation's declared `Result` and then casts the returned value to it; `cast` is a no-op, so the operation's answer is whatever the method returned. The documented invariant "it must return a typed `Result`" holds by convention alone.

---

## P3 — `ActionResultTypeError` is raised nowhere

The probe lives at `evidence/probes/p3_dead_error.py` and prints both the raise sites and every mention.

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/probes/p3_dead_error.py
```

Output:

```text
raise sites: 0
mentions: 7
   packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py:12
   packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py:68
   packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py:69
   packages/aoa-action-machine/src/aoa/action_machine/exceptions/action_result_type_error.py:2
   packages/aoa-action-machine/src/aoa/action_machine/exceptions/action_result_type_error.py:5
   packages/aoa-action-machine/src/aoa/action_machine/runtime/error_handler_executor.py:154
   packages/aoa-action-machine/src/aoa/action_machine/runtime/error_handler_executor.py:43
```

**What it proves**: the class exists and is exported, is imported and caught by the error-handler path, and is never raised anywhere in the package. The issue credits that path with validating a handler's result; on this tree it does not. The specification records the discrepancy and does not claim the handler path refuses anything.

**Consequence for the plan**: the class is the name the answer rule will take (`FR-019`), which revives a dead public name instead of adding a fourth one.

---

## What these three do not establish

- They say nothing about the types the annotations resolve to — that needs the operation's own `Params` and `Result`, which exist only at assembly, and is measured by the tests of US2, not here.
- They are probes, not tests: they live under `evidence/probes/` so the before/after pair can be reproduced, but the permanent form of these assertions is the test suite written in T007–T028, which must fail on the tree as it stands and pass after the change.
