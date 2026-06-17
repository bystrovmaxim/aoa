<!-- translated-from: step-23-testbench_draft.md @ 2026-06-17T17:53:37Z · sha256:6be65b97f4a6 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 23 — TestBench: the same Action, a different reality

<table width="100%"><tr>
  <td align="left"><a href="step-22-lifecycle.md">← Step 22 — Lifecycle</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-24-substitution.md">Step 24 — Substituting the environment →</a></td>
</tr></table>

- [Why the same Action](#why-the-same-action)
- [Run depth](#run-depth)
- [The whole operation](#the-whole-operation)
- [A single aspect](#a-single-aspect)
- [The summary alone](#the-summary-alone)
- [A compensator as a unit](#a-compensator-as-a-unit)
- [@on_error via a full run](#on_error-via-a-full-run)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The **Data model** part described the domain. The **Testing** part answers how to verify all of it without breaking the tests on every refactor.

An ordinary test assembles a separate world of mocks around a scenario and checks the agreement with the mocks, not the scenario's behavior; over time the mock stops reflecting the real resource, yet the test is still green. AOA does not substitute the scenario itself: `TestBench` runs the **same `Action` through the same machine** — the pipeline, checkers, roles, `@depends`, plugins are all real — and substitutes only the **reality around it**.

This chapter is about **what you can run**: at what depth to run an operation. What to substitute that reality with (`with_mocks`, connections, Rollup) is the [next chapter](../index.md#v-testing); assembling the context (`with_user`/…) is the [one after](../index.md#v-testing). Here `with_user` is used minimally, so that `@check_roles` passes.

[▶ Try in Colab](https://drive.google.com/file/d/10eZ6dRuYxf41lXlII-oDGb6LczZCBTg-/view?usp=drive_link) · [Open in project](../../examples/step_23_testbench/01_testbench.py)

---

## Why the same Action

The key principle: [an operation holds no state between calls](step-01-action-and-pipeline.md). Everything that affects execution comes from outside — `Params`, `Context`, the pipeline `state`, `connections`, `@depends` dependencies, the machine's plugins. Hence the simplicity of testing: there is no need to bring an object to some internal state in advance — it is enough to assemble the right input and environment, and the scenario stays real.

## Run depth

`TestBench` runs an operation at different depths — tests scale by risk:

| Method | What it checks |
|--------|----------------|
| `run` | the whole operation, production-like |
| `run_aspect` | one `@regular_aspect`: its input `state` and step result |
| `run_summary` | only the `@summary_aspect`: building `Result` from a ready `state` |
| `run_compensator` | one compensator as a unit |
| (a full `run`) | `@on_error` — there is no separate runner, the error is triggered through `run` |

On `run`, `run_aspect`, `run_summary` the `rollup` argument is **mandatory and has no default** — the test author explicitly chooses the mode (here everywhere `rollup=False`; the Rollup mode itself is in the next chapter).

## The whole operation

`run(action, params, rollup=...)` — a production-like run through the machine: access, aspects, sagas, errors. In the example the operation is real, while the payment gateway is replaced with a mock:

```python
result = await bench.run(ChargeAction(), params, rollup=False)
# -> txn=txn-001 amount=1500.0
```

## A single aspect

`run_aspect(action, "name", params=, state=, rollup=)` runs one `@regular_aspect` and returns the `state` after it. You supply the input `state`, check the step result and its checkers — in isolation from the rest of the pipeline:

```python
state_after = await bench.run_aspect(ChargeAction(), "charge_aspect", params=params, state={}, rollup=False)
state_after["txn_id"]   # "txn-002"
```

## The summary alone

`run_summary(action, params=, state=, rollup=)` builds `Result` from a **ready** `state`, without touching the regular aspects. Convenient to check exactly the result assembly:

```python
result = await bench.run_summary(ChargeAction(), params=params, state={"txn_id": "txn-pre"}, rollup=False)
# txn=txn-pre, while gateway.charge was never called
```

## A compensator as a unit

A [compensator](step-04-saga-and-compensations.md) usually fires when a later saga step fails. To test it separately, without building out the whole saga, there is `run_compensator` — the analogue of `run_aspect` for a compensator: you pass `params`, `state_before`, `state_after`, and `error` directly:

```python
await bench.run_compensator(
    ChargeAction(), "charge_compensate",
    params=params,
    state_before=BaseState(),
    state_after=BaseState(txn_id="txn-004"),
    error=RuntimeError("later step failed"),
)
# the compensator called gateway.refund("txn-004")
```

An important subtlety: `run_compensator` **does not suppress** exceptions (in production `_rollback_saga` silences compensator errors). This is deliberate — so that in a test you can check that the compensator does not fail in the norm, survives an internal failure correctly, or, conversely, fails in a specific edge case.

## @on_error via a full run

There is no separate `run_on_error`: [`@on_error`](step-05-error-handling.md) is checked with a **full `run`** that provokes the error. Make the mock throw the needed exception — the handler will catch it and return a `Result`:

```python
gw.charge.side_effect = ValueError("card declined")
result = await bench.run(ChargeAction(), params, rollup=False)
# txn=declined — @on_error(ValueError) fired
```

**Run:**

```bash
uv run python examples/step_23_testbench/01_testbench.py
```

**Output:**

```text
1) run (whole Action)        -> txn=txn-001 amount=1500.0
2) run_aspect (charge_aspect)-> state.txn_id=txn-002
3) run_summary               -> txn=txn-pre  (charge called: False)
4) run_compensator           -> gateway.refund('txn-004') called: True
5) run + @on_error(ValueError) -> txn=declined  (handler returned a Result)
```

The same `ChargeAction` is checked at five depths — whole, by step, by result assembly, by compensator, and by the error branch — and everywhere through the real machine.

## Invariants

- **The scenario is real.** The same `Action`, the same machine and pipeline; only the reality around it changes.
- **No state between calls.** A test = assembling the input and environment, not "warming up" an object.
- **Depth at will.** `run` (the whole operation) / `run_aspect` (a step) / `run_summary` (result assembly) / `run_compensator` (a compensator); `@on_error` — through a full `run`.
- **`rollup` is set explicitly.** On `run`/`run_aspect`/`run_summary` — a mandatory argument with no default.
- **A compensator in a test is not silenced.** `run_compensator` propagates the exception (unlike the production saga rollback).

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

`TestBench` checks the same operation through the same machine, changing only the environment — this works because the operation carries no state between calls. You can run it at the needed depth: the whole operation (`run`), a single regular aspect (`run_aspect`), result assembly (`run_summary`), a compensator as a unit (`run_compensator`), and the `@on_error` branch with a full run that provokes the error. Tests thus scale by risk while staying production-like.

Next — **[Substituting the environment](step-24-substitution.md)**: how `with_mocks` substitutes dependencies and resources, how `@connection` is supplied, and how Rollup works.

---

## Review questions

1. Why can a test "lie" by checking the agreement with mocks? What does AOA substitute instead of the scenario?
2. From which property of an `Action` does it follow that a test does not need to set up an object in advance?
3. At what depths can an operation be run, and what does each level check? Where in this row is `@on_error`?
4. Why is `rollup` a mandatory argument with no default?
5. How does `run_compensator` differ from the production saga rollback regarding errors, and why is this needed in a test?
6. How do you check the `@on_error` branch if there is no separate runner for it?

> **Exercise.** In [01_testbench.py](../../examples/step_23_testbench/01_testbench.py) add a `run_aspect` for the case where `gateway.charge` throws an exception, and trace where the error surfaces (in `run_aspect` itself, not in `@on_error`). Then through `run_summary` supply a `state` without `txn_id` and explain which error this turns into and why — this is exactly the check of the result-assembly contract.

---

<table width="100%"><tr>
  <td align="left"><a href="step-22-lifecycle.md">← Step 22 — Lifecycle</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-24-substitution.md">Step 24 — Substituting the environment →</a></td>
</tr></table>
