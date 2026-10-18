# Adversarial evidence — US4, a summary's answer is its operation's Result

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T031 | **Date**: 2026-10-18

The rule has two halves. At assembly the summary's declared return must name the operation's
`Result` — that was implemented with US2 and is pinned here as this story's contract. At run time
the returned value is compared with the same `Result`, which is the only half that can catch a
method contradicting its own annotation.

## The break — the run-time comparison removed

```python
        if False:  # ADVERSARIAL BREAK: the answer is not compared with the Result
```

```bash
.venv/bin/python -m pytest \
  packages/aoa-action-machine/tests/action_machine/runtime/test_summary_answer_contract.py -q
```

```text
2 failed, 9 passed in 0.08s
```

The two are exactly the run-time cases: a summary annotated `-> ResultStub` that returns a dict, and
one that returns another operation's `Result`. The nine that kept passing are the assembly cases,
the compliant run, and the three invariance assertions — a comparison that stops checking does not
disturb the answer of an operation that was already correct.

## Restoration

```text
11 passed in 0.04s
```

## The pre-change behaviour this closes

Measured on the tree before the change (`evidence/baseline.md`, probe P2): the same operation
answered with `{'not': 'a result'}`, `is ResultStub: False`, and no layer objected. The refusal now
names the operation, the method, the declared `Result` and the type that actually came back:

```text
ActionResultTypeError: MappingAnswerAction.mapping_answer_summary returned dict, but the
operation declares Result ResultStub.
```

## What the error carries

`ActionResultTypeError` was already public, already exported and raised nowhere; it requires
`expected_type` and `actual_type` keyword-only arguments for adapters, so the check fills them from
the resolved `Result` and the returned value's type rather than re-inventing a new exception. That
is the vocabulary decision recorded in the specification, made real at last.
