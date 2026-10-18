# Performance evidence — what the answer check costs on the exit path

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T032 | **Date**: 2026-10-18

**Base commit**: `7dc5cbf3`. **Environment**: Python 3.12.12, one machine, one session, warm-up of 100 runs
before each measurement.

## What is measured

One compliant operation — `ParamsStub`, `ResultStub`, a single summary returning its own result — run
**10 000 times** through `ActionProductMachine.run`. The only difference between the two runs is the
line the change adds: an `isinstance` comparison of the returned value with the operation's `Result`,
plus the `result_type` binding that replaced a discarded `resolve_result_type` call.

The probe is `/tmp/bench_exit.py`, deliberately outside the repository: it is a measurement, not a
check, and a timing assertion in the suite would be flaky by nature.

## The numbers

| Tree | Run 1 | Run 2 | Per run |
| --- | --- | --- | --- |
| Without the comparison (the tree before this step) | 0.281 s | 0.286 s | 28.1 / 28.6 µs |
| With the comparison (the tree after this step) | 0.281 s | 0.275 s | 28.1 / 27.5 µs |

The spread between the two runs of the *same* tree is larger than the spread between the trees:
0.281–0.286 s versus 0.275–0.281 s. One `isinstance` on a 28 µs path is below the measurement's own
noise, which is what the plan predicted when it set the target at "at most 5 % longer".

## How to read it

- **Not a benchmark of the framework.** It measures one line's marginal cost against a full pipeline
  run, which is the question this change asked: does the check make the exit path slower enough to
  notice?
- **Not an assertion.** No test pins these numbers, because a timing assertion fails on a loaded
  machine and teaches nothing. The guard against a real regression is that the check is one
  `isinstance` over a value the operation already holds.
- **The resolved type is now used, not discarded.** Before the change the exit path called
  `resolve_result_type(action_cls)` and threw the answer away; the change keeps it, so the comparison
  costs a reference binding the code was already paying for the call.
