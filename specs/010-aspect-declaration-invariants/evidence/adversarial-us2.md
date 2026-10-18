# Adversarial evidence — US2, the types a declaration is judged by

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T024 | **Date**: 2026-10-18

Two validators carry this story: `validate_annotated`, which requires an annotation where the
method is written, and `validate_types`, which resolves those annotations when the capability is
assembled. Each was disabled in turn, the test file was run, and the failures were compared with
the rules the validator serves. The code was restored after each break and the whole tree re-verified.

## Break 1 — `validate_annotated` returns immediately

```python
    return  # ADVERSARIAL BREAK: annotations are not required
    parameters = inspect.signature(func).parameters
```

```bash
.venv/bin/python -m pytest \
  packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_types.py -q
```

```text
4 failed, 15 passed in 0.06s
```

The four are exactly the annotation rule: a bare parameter, a bare return, the same discipline in
each of the other three decorators, and the message that must say the class body was still
executing. The fifteen assembly-time tests kept passing — a validator that stops checking
annotations does not cover for the one that checks their types.

## Break 2 — `validate_types` returns immediately

```python
    return  # ADVERSARIAL BREAK: annotation types are not checked
    hints = _resolved_hints(contract, action_cls, func)
```

```text
10 failed, 9 passed in 0.09s
```

The ten are every assembly-time rule: the wrong `box`, the bare `connections`, the wrong `state`,
the bare `error`, the summary's `Any` and the foreign `Result`, the regular aspect's `str`, the
compensator's mapping, the unresolvable name, and the moment the message names. The nine that kept
passing are the declaration-time cases and the three "accepted" ones.

## Restoration

```bash
for pkg in aoa-action-machine aoa-demo aoa-maxitor aoa-langgraph aoa-otel aoa-ocel \
           aoa-mcp-adapter aoa-fastapi-adapter; do
  .venv/bin/python -m pytest packages/$pkg/tests -q
done
```

```text
aoa-action-machine     2596 passed
aoa-demo                 73 passed
aoa-maxitor             134 passed, 1 skipped, 1 xfailed
aoa-langgraph            87 passed
aoa-otel                 63 passed
aoa-ocel                 26 passed
aoa-mcp-adapter         130 passed
aoa-fastapi-adapter     161 passed
```

```bash
.venv/bin/python -m ruff check packages/
.venv/bin/python -m mypy .../intents/aspects/ .../graph/nodes/
```

```text
All checks passed!
Success: no issues found in 29 source files
```

## What the pass revealed about the rule itself

The first version of `_validate_error` required the annotation to be **exactly** `Exception`. The
demo suite refused at import: a real operation annotates its handler with the exception it was
declared for (`error: ValueError`), which is true — the executor dispatches per declared type, so a
`ValueError` handler never receives a `TypeError`. The rule was corrected to accept any `Exception`
subclass, and the refusal now reads "Exception or a subclass of it". That is the adversarial pass
doing its job on the rule rather than on the code.

It also found two drawing fixtures in the demo (`GeneralizationFirstChildAction`,
`GeneralizationSecondChildAction`) whose summary returned their *own* nested `Result` while the
operation's declared `Result` — resolved from the parent's `BaseAction[...]` — was the parent's. The
two classes were unrelated, so the fixture had been promising one answer and returning another since
it was written; nothing compared them until now. Both children now declare their own `BaseAction`
arguments, which is what their bodies always meant, and the shape the demo draws is unchanged.

## The corpus work this phase pulled in

The assembly rules cannot be satisfied by annotations that merely exist: 256 parameters under
`packages/` were annotated `Any` (`box: Any`, `state: Any`, `connections: Any`) and 12 more named
`ctx: object` or `ctx: Any`. All of them were replaced with the contract types — 53 files, plus the
imports those types need. Without that, every graph build in the suite refused at assembly, which is
how the size of that laziness became visible at all.
